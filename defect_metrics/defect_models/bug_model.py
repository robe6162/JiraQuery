from collections import OrderedDict
from dataclasses import dataclass
import typing

from defect_metrics.config.cfg_mappings import ConfigFileType
import defect_metrics.logging.logger as logger


logging = logger.Logger()


@dataclass
class BugKeys:
    ASSIGNEE: str = 'assignee'
    BUG_TYPE: str = 'bug_type'
    COMPONENT: str = 'component'
    CREATED: str = 'created'
    DATE_DELIMITER: str = '/'
    DEFECT_ID: str = 'defect_id'
    DESCRIPTION: str = 'description'
    DETECTED: str = 'detected'
    ENVIRONMENT: str = 'environment'
    FIXED_IN: str = 'fixed'
    HISTORY: str = 'history'
    ITEMS: str = 'items'
    ISSUES: str = 'issues'
    LABELS: str = 'labels'
    LINK: str = 'link'
    PILLAR: str = 'pillar'
    PRIORITY: str = 'priority'
    PROJECT: str = 'project'
    REPORTER: str = 'reporter'
    SEVERITY: str = 'severity'
    SOURCE: str = 'source'
    STATES: str = 'states'
    STATES_SUMMARY: str = 'states_summary'
    STATUS: str = 'status'
    TITLE: str = 'title'
    VALID: str = 'valid'
    VERSION: str = 'version'


class RequiredFields:
    PRIORITY = BugKeys.PRIORITY
    SEVERITY = BugKeys.SEVERITY
    ENVIRONMENT = BugKeys.ENVIRONMENT
    COMPONENT = BugKeys.COMPONENT
    REQUIRED = [COMPONENT, ENVIRONMENT, PRIORITY, SEVERITY]


class Bug(object):
    def __init__(self, **kwargs):
        self._defect_id = kwargs.get(BugKeys.DEFECT_ID)
        self._status = kwargs.get(BugKeys.STATUS)
        self._project = kwargs.get(BugKeys.PROJECT)
        self._title = kwargs.get(BugKeys.TITLE)
        self._description = kwargs.get(BugKeys.DESCRIPTION)
        self._priority = kwargs.get(BugKeys.PRIORITY)
        self._severity = kwargs.get(BugKeys.SEVERITY)
        self._environment = kwargs.get(BugKeys.ENVIRONMENT)
        self._version = kwargs.get(BugKeys.VERSION)
        self._pillar = kwargs.get(BugKeys.PILLAR)

        self._link = kwargs.get(BugKeys.LINK)
        self._assignee = kwargs.get(BugKeys.ASSIGNEE)
        self._reporter = kwargs.get(BugKeys.REPORTER)
        self._fixed_in = kwargs.get(BugKeys.FIXED_IN)
        self._labels = kwargs.get(BugKeys.LABELS)
        self._history = kwargs.get(BugKeys.HISTORY, [])
        self._states_summary = kwargs.get(BugKeys.STATES_SUMMARY, [])
        self._detected = kwargs.get(BugKeys.DETECTED)

        self._bug_type = kwargs.get(BugKeys.BUG_TYPE)
        self._component = kwargs.get(BugKeys.COMPONENT)
        self._created = kwargs.get(BugKeys.CREATED)
        self._source = kwargs.get(BugKeys.SOURCE)
        self._valid = kwargs.get(BugKeys.VALID, True)
        self._states = kwargs.get(BugKeys.STATES, {})

        self.reportable_attributes = [
            'defect_id', 'title', 'project', 'severity', 'component_list', 'labels', 'priority', 'status', 'detected',
            'fixed_in', 'created', 'states_list', 'reporter', 'assignee', 'is_valid', 'pillar', 'states_unique_summary',
            'link']

    def __str__(self):
        fmt = """
    Id: {defect_id}
        Pillar: {pillar}
        Project: {project}
        Link: {link}
        Title: '{title}'
        Status: {status}
        Created: {created}
        Valid Defect? {is_valid!s}
        Component(s): {component_list}

        Priority: {priority}
        Severity: {severity}
        When Detected: {detected}
        
        States: {states_list}
        Concise Summary: {states_unique_summary}"""

        data = self.as_dict()
        return fmt.format(**data)

    def _get_data(self) -> typing.Dict[str, str]:
        # Attributes to return (in semi-logical order)
        return OrderedDict([(attr, getattr(self, attr)) for attr in self.reportable_attributes])

    def as_dict(self):
        return self._get_data()

    @property
    def defect_id(self):
        return self._defect_id

    @property
    def pillar(self):
        return self._pillar

    @property
    def project(self):
        return self._project

    @property
    def status(self):
        return self._status.capitalize()

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def priority(self):
        return self._priority

    @property
    def severity(self):
        return self._severity

    @property
    def environment(self):
        return self._environment

    @property
    def version(self):
        return self._version

    @property
    def bug_type(self):
        return self._bug_type

    @property
    def component_list(self):
        return ', '.join(self._component)

    @property
    def component(self):
        return self._component

    @property
    def created(self):
        return self._created

    @property
    def source(self):
        return self._source

    @property
    def states(self):
        return self._states

    @property
    def states_list(self):
        summary = '\n'
        for state_tuple in self._states:
            summary += f"\t\t{state_tuple.actual:25} ({state_tuple.standard}):   {str(state_tuple.timestamp)}\n"
        return summary

    @property
    def states_summary(self):
        return self._states_summary

    @property
    def states_unique_summary(self):
        reduced_unique = []
        previous = None
        for state in self._states_summary:
            if state != previous:
                reduced_unique.append(state)
            previous = state
        return reduced_unique

    @property
    def is_valid(self):
        return self._valid

    @property
    def link(self):
        return self._link

    @property
    def assignee(self):
        return self._assignee

    @property
    def reporter(self):
        return self._reporter

    @property
    def detected(self):
        return self._detected

    @property
    def fixed_in(self):
        return self._fixed_in

    @property
    def labels(self):
        return self._labels

    @property
    def history(self):
        return self._history


class Bugs(list):

    def __init__(self, bug_list: typing.List = None, mapping: ConfigFileType = None) -> typing.NoReturn:
        super(Bugs, self).__init__()
        self.mapping = mapping
        if bug_list is not None:
            for bug in bug_list:
                self.append(bug)

    def add(self, bug: Bug) -> Bug:
        self.append(bug)
        return bug

    def validate(self, filename: str = None) -> typing.Dict:
        issues = {}
        for bug in self:
            reporter = str(getattr(bug, BugKeys.REPORTER))
            defect_link = str(getattr(bug, BugKeys.LINK))

            for field in RequiredFields.REQUIRED:
                field_value = getattr(bug, field, None)

                # If required field is None or blank, log it!
                if field_value is None or field_value == '':

                    # Build out tracking dictionary as needed
                    if reporter not in issues:
                        issues[reporter] = OrderedDict()
                    if defect_link not in issues[reporter]:
                        issues[reporter][defect_link] = list()

                    issues[reporter][defect_link].append(str(field))

        # Write issues to file if requested
        if filename is not None and issues:
            with open(filename, "w") as ISSUES:
                for reporter, defects in issues.items():
                    ISSUES.write("Reporter: {0}\n".format(reporter))
                    for link, missing in defects.items():
                        defect_id = link.split('/')[-1]
                        fields = ', '.join(missing)
                        ISSUES.write("\t{id_}: {fields}\n".format(
                            id_=defect_id, fields=fields))
                    ISSUES.write('\n')
            logging.info(f"*** Issues found: Recorded in {filename}")
        return issues
