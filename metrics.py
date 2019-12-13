#!/usr/bin/env python

import typing

from defect_metrics.config.cfg_mappings import get_configuration, get_pillars
from defect_metrics.config.command_line import CommandLine
from defect_metrics.jira_client.jira_client import JiraClient
from defect_metrics.jira_client.jira_mappings import JiraFields
import defect_metrics.logging.logger as logger
from defect_metrics.metrics.bouncemetrics import BounceMetrics

BORDER_CHAR = "+"
BORDER_LENGTH = 120
BORDER = BORDER_CHAR * BORDER_LENGTH
DEFECT_TYPE = "defect"


def format_date(date_string: str) -> str:
    """
    Format the strinh date provided on the CLI

    :param date_string: string of date : YY/MM/DD

    :return: str of date with full formatting

    """
    delimiter = "/"
    year, month, day = date_string.split('-')
    if int(year) < 100:
        year = f"20{year}"
    return f"{year}{delimiter}{int(month):02}{delimiter}{int(day):02}"


def get_jira_data(client: JiraClient, pillar: str, projects: typing.List[str],
                  logging: logger.Logger, status: str = None) -> typing.Dict[str, dict]:
    """
    Query Jira for the requested data

    :param client: Instantiated Jira Client
    :param pillar:  Name of the pillar (used in storing data, not in the query)
    :param projects: List of Jira projects to query
    :param logging: Instantiated logging for recording data
    :param status: Query defects with a specific status

    :return: Dictionary: [pillar][project] --> List of defect (JSON data per defect)

    """
    all_defects = {pillar: {}}

    # Iterate through projects defined in pillar
    for project in projects:
        logging.info(f"\n{BORDER}\n*     Querying defects for {pillar}:{project.upper()}\n{BORDER}\n")

        # Build Jira data filter
        query_params = {JiraFields.PROJECT: f"'{project}'", JiraFields.ISSUETYPE: DEFECT_TYPE}
        if status is not None:
            query_params[JiraFields.STATUS] = status

        # Query Jira
        results_list = client.query(query_params_dict=query_params)

        # Check for results and if found, store the populated Bug object list by pillar and project
        if results_list:
            all_defects[pillar][project] = results_list

        else:
            logging.info(f"No defect info was returned for {pillar}:{project}. "
                         f"\nPossible issues:\n"
                         "\t* there is a problem with the query,\n"
                         "\t* the query did not return any defect info, or\n"
                         "\t* Jira is not allowing the query to execute. Enable debug to assess issue.\n\n")
            all_defects[pillar][project] = []

    return all_defects


def main(cli_args: CommandLine) -> typing.NoReturn:

    # List pillars and projects if requested.
    if cli_args.args.list:
        print(get_pillars(cli_args.args.cfg))
        exit()

    # Create date str '.yyyymmdd.yyyymmdd' if dates are provided
    dates = [format_date(cli_args.args.start), format_date(cli_args.args.end)]
    date_str = f".{dates[0].replace('/', '')}.{dates[1].replace('/', '')}" if dates else "."

    # If ALL reports are to be run, update pillar list to include all defined pillars.
    pillar_list = cli_args.args.pillar
    if CommandLine.consts.ALL.lower() in [x.lower() for x in pillar_list]:
        pillar_list = get_pillars(cli_args.args.cfg)

    # Determine log file name
    logfile = f"defects{date_str}.log"
    if len(pillar_list) == 1:
        logfile = f"defects{date_str}.{pillar_list[0]}.log"

    logging_level = logger.Logger.STR_TO_VAL['debug' if cli_args.args.debug else 'info']
    logging = logger.Logger(default_level=logging_level, filename=logfile, project="defect_metrics", set_root=True)

    for pillar in pillar_list:
        print(f"+{BORDER}+\n|{pillar:^{BORDER_LENGTH}}|\n+{BORDER}+\n")
        results_file = f"defects.{pillar}{date_str}.{{metric}}.report"

        # Setup logging
        logging.debug(f"Logging Project: {logging.project}")

        # Get Jira and Pillar configurations
        cfg_map = get_configuration(mapping_file=cli_args.args.cfg, pillar=pillar)
        jira_url = cfg_map.get_url()
        defined_projects = cfg_map.get_projects()

        # Log the query parameters
        logging.info(f"\n\nPILLAR: {pillar}\nPROJECTS: {defined_projects}\n"
                     f"URL: {jira_url}\nDates: {dates[0]} to {dates[1]}\n")

        # Instantiate client
        client = JiraClient(jira_url=jira_url, username=cli_args.args.user, pswd=cli_args.args.pswd,
                            pillar=pillar, mapping=cfg_map, date_range=dates)

        # Get the defect data
        defects = get_jira_data(client=client, pillar=pillar, projects=defined_projects, logging=logging)

        # Calculate and record the Bounce Rate metrics
        BounceMetrics(pillar=pillar, pillar_data=defects, dates=dates).write_report(filename=results_file)

    logging.info("Processing complete.")


if __name__ == "__main__":
    main(CommandLine())
