#!/usr/bin/env python

from collections import namedtuple
from dataclasses import dataclass
import datetime
import json
import pprint
import typing
import urllib

import requests

from defect_metrics.config.cfg_mappings import ConfigFileType
from defect_metrics.defect_models.bug_model import Bug, Bugs, BugKeys
from defect_metrics.jira_client.jira_mappings import JiraFields
import defect_metrics.logging.logger as logger

logging = logger.Logger()


@dataclass
class DefectKeys:
    """

    Keywords used in tracking data structures

    """
    ASSIGNEE: str = 'ASSIGNEE'
    CHANGELOG: str = 'changelog'
    DEFECT: str = 'defect'
    DETECTED: str = 'DETECTED'
    EXPAND: str = 'expand'
    KEY: str = 'KEY'
    NAME: str = 'NAME'
    PRIORITY: str = 'PRIORITY'
    PROJECT: str = 'PROJECT'
    REPORTER: str = 'REPORTER'
    SEVERITY: str = 'SEVERITY'
    STATUS: str = 'STATUS'
    URL: str = 'url'
    VALUE: str = 'VALUE'


# Named tuple for tracking Jira state events
State = namedtuple('State', 'actual, standard, timestamp')


class JiraClient:
    """

    Routines for getting data from Jira.
    This class breaks the traditional rules that clients should only tx/rx data, as this client also processes
    the data and creates a Bug object per entry.

    """

    CLIENT_TYPE = 'JIRA'

    def __init__(self, jira_url: str, mapping: ConfigFileType, pillar: str, username: str = None,
                 pswd: str = None, date_range: typing.List[str] = None):
        self.url = jira_url
        self.auth = (username, pswd)
        self.mapping = mapping
        self.pillar = pillar
        self.date_range = date_range or []

        self.verb = "updated"

    def query(self, query_params_dict: typing.Dict) -> Bugs:
        """
        Makes a request to the specified Jira instance.

        :param query_params_dict: Dictionary of parameters (AND'D) to be used to build the JQL query

        :return: A list of populated Bug objects - 1 Bug object per record returned.

        """

        # Crate the list to populate
        defects = Bugs(mapping=self.mapping)

        params = 'AND'.join([" {} = {} ".format(k, v) for k, v in query_params_dict.items()])

        # Add date range, if defined.
        if self.date_range is not None:
            dates = f'{self.verb} >= "{self.date_range[0]}" AND {self.verb} <= "{self.date_range[1]}"'
            params += f"AND {dates} "

        params = urllib.parse.quote_plus(params)

        # Build the JQL URL
        url = f'{self.url}/rest/api/2/search?jql={params}'
        logging.debug(f"DEBUG: URL: {url}")

        # Make the request
        response = requests.get(url=url, auth=self.auth)
        if response.status_code == requests.codes.ok:
            issues = self._deserialize_content(response.content, key=JiraFields.ISSUES)

            # logging.debug(f"\n{pprint.pformat(issues)}")
            logging.debug(f"NUM ISSUES: {len(issues)}")

            # For each issue returned, deserialize into a Bug object
            for issue in issues:
                defect_obj = self._decompose_bug_entry(bug_entry=issue)
                defects.append(defect_obj)

        else:
            logging.error(f'ERROR: Response Code = "{response.status_code}" for URL: {url}')
            logging.error(f'\nURL Response:\n\t{response.content}\n')

        return defects

    @staticmethod
    def _deserialize_content(content: typing.Dict, key: str = '') -> typing.Dict:
        """
        Process the responses returned from Jira (convert from JSON into Python structure)

        :param content: Raw responses from JIRA
        :param key: String key if JSON data has primary level key.

        :return: (Dict) Python data structure that matches JSON data

        """
        deserialized_content = None
        try:
            json_resp = json.loads(content)
        except Exception as err:
            logging.error(f"ERROR: Unable to decode json:\n{err}")
        else:
            deserialized_content = json_resp.get(key, json_resp)
        return deserialized_content

    def _decompose_bug_entry(self, bug_entry: typing.Dict) -> Bug:
        """
        Deserialize JIRA python structure into a Bug object

        :param bug_entry: Data (from _desrialize_content)

        :return: Instantiated, populated Defect obj

        """

        web_url_fmt = '{url}/browse/{defect}'

        bug_data = {}

        # Simplify the JSON call reference, since all fields have a common
        # ancestor. (Shortens the length of call to get target value.)
        bug_fields = bug_entry.get(JiraFields.FIELDS)

        defect_id = str(bug_entry.get(JiraFields.DEFECT_ID))
        project = defect_id.split('-')[0].lower()

        # Store basic defect information
        bug_data[BugKeys.PILLAR] = self.pillar
        bug_data[BugKeys.DESCRIPTION] = bug_fields.get(JiraFields.DESCRIPTION)
        bug_data[BugKeys.TITLE] = str(bug_fields[JiraFields.SUMMARY])
        bug_data[BugKeys.DEFECT_ID] = defect_id
        bug_data[BugKeys.SOURCE] = self.CLIENT_TYPE

        # Get hyperlinks
        link_args = {DefectKeys.URL: self.url, DefectKeys.DEFECT: defect_id}
        bug_data[BugKeys.LINK] = web_url_fmt.format(**link_args)

        # Get Created timestamp
        bug_data[BugKeys.CREATED] = datetime.datetime.strptime(
            (str(bug_fields.get(JiraFields.CREATED)).split('+'))[0], '%Y-%m-%dT%H:%M:%S.%f')

        # For values that are nested down a second layer in the JSON:
        # data {ATTRIBUTE_NAME_1: {VALUE_NAME: value,
        #                          some_other_attr: <whatever>, ... },
        #       ATTRIBUTE_NAME_2: {VALUE_NAME: value,
        #                          some_other_attr: <whatever>, ... },
        #
        # ------------------------------------------------------------
        # DICTIONARY (compound_attributes)
        # PRIMARY KEY: The name of the end attribute: VALUE_NAME
        # LIST VALUES: List of the ATTRIBUTE_NAMES to retrieve

        compound_attributes = {
            DefectKeys.NAME: [DefectKeys.ASSIGNEE, DefectKeys.REPORTER, DefectKeys.PRIORITY, DefectKeys.STATUS],
            DefectKeys.KEY: [DefectKeys.PROJECT],
            DefectKeys.VALUE: [DefectKeys.SEVERITY, DefectKeys.DETECTED]
        }

        logging.debug(f"Pillar: {self.pillar}")
        logging.debug(f"Project: {project.upper()}")
        logging.debug(f"Defect ID: {defect_id}")

        # logging.debug(f"\n{pprint.pformat(self.mapping.mappings)}")
        # logging.debug(f"Bug Fields\n{pprint.pformat(bug_fields)}")

        # Get the data defined in the compound_attributes dictionary, based on expected key in the JSON
        for data_field, parent_attr_list in compound_attributes.items():

            # For each expected key in the nested JSON
            for attr_name in parent_attr_list:

                # Get the keywords required to pull the data
                attr_name = str(attr_name)
                defect_attr = str(getattr(BugKeys, attr_name))
                parent_attr = str(getattr(JiraFields, attr_name))
                value_attr = getattr(JiraFields, data_field)

                # Try to extract the data
                try:
                    bug_data[defect_attr] = bug_fields[parent_attr][value_attr]
                except (KeyError, TypeError):
                    bug_data[defect_attr] = None
                    logging.warn(f"{defect_id} --> Did not find: {defect_attr}")
                else:

                    # Translate status to accepted QE statuses...
                    if attr_name == DefectKeys.STATUS:
                        mapping = self.mapping.mappings[self.pillar]
                        try:
                            bug_data[defect_attr] = mapping[str(bug_data[defect_attr]).lower()].lower()
                        except KeyError:
                            logging.error(
                                f"{defect_id} --> Unrecognized Defect Status: '{bug_data[defect_attr].lower()}'. "
                                f"Need to add and classify the defect.")
                            continue

        # Process the fields that contain lists
        comp_list_fields = bug_fields.get(JiraFields.COMPONENTS)
        bug_data[BugKeys.COMPONENT] = [str(comp.get(JiraFields.NAME)) for comp in comp_list_fields]

        fixed_ver_list = bug_fields[JiraFields.FIXED_VERSION]
        bug_data[BugKeys.FIXED_IN] = [str(ver.get(JiraFields.NAME)) for ver in fixed_ver_list]

        bug_data[BugKeys.LABELS] = [str(lbl) for lbl in bug_fields[JiraFields.LABELS]]

        # Scrape change_log for history of defect state changes
        change_log = self._get_change_log(bug_data[BugKeys.DEFECT_ID])

        # Store the change log
        bug_data[BugKeys.ITEMS] = change_log

        # Get the status transition history, the normalized status, and the basic workflow (state_summary)
        transition_data, states, normalized_states = self._parse_change_log(
            change_log, defect_id=defect_id, create_time=bug_data[BugKeys.CREATED])

        bug_data[BugKeys.STATES] = transition_data
        bug_data[BugKeys.HISTORY] = states
        bug_data[BugKeys.STATES_SUMMARY] = normalized_states

        # Build the Bug object
        defect = Bug(**bug_data)
        logging.info(f"DEFECT {defect.defect_id}:\n{str(defect)}\n")

        return defect

    @staticmethod
    def _update_status(bug_data: typing.Dict) -> typing.NoReturn:
        """
        Update status for development that has a non-new classification, but all state transitions are empty

        :param bug_data: Dictionary with data to be used to create a Bug object

        :return: None

        """

        # Get all states and transitions
        transitions = bug_data[BugKeys.STATES]
        states = [x.lower() for x in transitions.keys()]

        # logging.debug(f"Transitions: {pprint.pformat(transitions)}")
        # logging.debug(f"DEFINED STATES: {', '.join(states)}")

        # Check if it is the 'NEW' state. If so, open (states[1]) will be None
        update_status = transitions[states[1]] is None
        for state in states[2:]:
            update_status = update_status & (transitions[state] is None)
        if update_status:
            bug_data[BugKeys.STATUS] = str(states[0]).lower()

    def _get_change_log(self, defect_id: str) -> typing.Dict:
        """
        Get the defect's change log (this requires an additional query to Jira)

        :param defect_id: ID of the defect

        :return: Deserialized JSON data structure (dict)

        """
        url = f'{self.url}/rest/api/2/issue/{defect_id}'
        params = {DefectKeys.EXPAND: DefectKeys.CHANGELOG}
        response = requests.get(url=url, params=params, auth=self.auth)
        return self._deserialize_content(content=response.content)

    def _parse_change_log(self, change_log_json: typing.Dict, defect_id: str, create_time: datetime.datetime) -> \
            typing.Tuple[typing.List[typing.Tuple[str, str, datetime.datetime]], typing.List[str], typing.List[str]]:

        """
        Parse the change logs to get state changes and corresponding timestamps

        :param change_log_json: deserialized JSON response
        :param defect_id: (str) Defect ID (used for logging purposes only)
        :param create_time: (datetime) Used to add 'new' state to list.

        :return: Tuple of the following:
            List of Tuples (state change, normalized state change, time stamp)
            List of Complete State Transitions
            List of Normalized State Transitions

        """
        # Define state change list and add the "new" or created state since that is not in the change log history)
        state_changes = [State(actual=self.mapping.order[0],
                               standard=self.mapping.order[0],
                               timestamp=create_time)]

        try:
            chg_logs = change_log_json[JiraFields.CHANGE_LOG][JiraFields.HISTORIES]

        except (KeyError, TypeError) as err:
            logging.error(f"Exception Thrown for {defect_id}: {err}")
            logging.error(f"ERROR: Unable to get the ChangeLog:\n{pprint.pformat(change_log_json)}")
            return state_changes, [st.actual for st in state_changes], self._normalize_states(state_changes)

        for chg in chg_logs:

            # Get the Defect history log (list)
            chg_item_list = chg[JiraFields.ITEMS]

            # Check each log transaction
            for item in chg_item_list:

                # If the field is a status field, this record will contain a status change.
                if item[JiraFields.FIELD].lower() == JiraFields.STATUS.lower():

                    # Get the original "change to" data
                    orig_chg_to = str(item[JiraFields.CHG_TO]).lower()

                    # If the pillar is not defined in the mappings, throw an error
                    if self.mapping.mappings.get(self.pillar, None) is None:
                        err = "ERROR: Pillar '{pillar}' is not defined in the mappings file: {file}"
                        logging.error(err.format(pillar=self.pillar, file=self.mapping.file))
                        return (state_changes,
                                [st.actual for st in state_changes],
                                self._normalize_states(state_changes))

                    # If the state is not defined in the mappings file, raise a warning and keep going
                    if orig_chg_to not in self.mapping.mappings[self.pillar]:
                        logging.warn(f"{defect_id}: Ignoring state change: {orig_chg_to}")
                        logging.warn(f"{chg}")
                        continue

                    # Covert the original state to a normalized (standard) change
                    std_chg_to = self.mapping.mappings[self.pillar][orig_chg_to]
                    chg_time = datetime.datetime.strptime(
                        str(chg[JiraFields.CREATED]).split('+')[0], '%Y-%m-%dT%H:%M:%S.%f')

                    state_changes.append(
                        State(actual=orig_chg_to, standard=std_chg_to, timestamp=chg_time))

        logging.debug(f"Change Log Timing Tuples: {pprint.pformat(state_changes)}")

        return state_changes, [st.actual for st in state_changes], self._normalize_states(state_changes)

    def _normalize_states(self, state_list: typing.List[State]) -> typing.List[str]:
        """
        Convert states to consistent set of states (e.g. - in development = open, in uat = test, etc.)
        :param state_list: List of State tuples

        :return: (List[str]) List of normalized states

        """
        rev_mapping = self.mapping.get_reverse_status_mappings()
        return [rev_mapping.get(state.actual) for state in state_list]

    def _validate_dates(self, change_dates: typing.Dict[str, datetime.datetime]) -> typing.NoReturn:
        """
        Make sure the dates are correct (the current date is the most recent date)

        :param change_dates: Dictionary of states and timestamps

        :return: None; just log issue
        """
        current_state = self.mapping.order[0]
        earliest = change_dates[current_state]
        errors = False
        for state in self.mapping.order:
            if change_dates[state] is not None and change_dates[state] < earliest:
                msg = "ERROR: Time in {next_state} is earlier than previous state '{curr_state}'."
                logging.debug(msg.format(next_state=state, curr_state=current_state))
                logging.debug(f"STATE ORDER: {', '.join(self.mapping.order)}")

                errors = True
        if errors:
            logging.error('BUG STATE LOGIC: "ORDER ERRORS"')
        else:
            logging.debug('BUG STATE LOGIC: OK')
