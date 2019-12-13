from dataclasses import dataclass
from datetime import datetime
import pprint
import typing

import prettytable

from defect_metrics.defect_models.bug_model import Bug, BugKeys
from defect_metrics.logging.logger import Logger
from defect_metrics.metrics.metrics_base import MetricsBase


""" This module will calculate and report the number of defects that were bounced. """

logging = Logger()


@dataclass
class BounceMetricConstants:
    SLA_LIMIT: int = 2

    BOUNCED: str = "bounced"
    CLOSED: str = "closed"
    OPEN: str = "open"
    TEST: str = "test"
    TOTAL: str = "total"
    VIOLATIONS: str = "violations"


class BounceMetrics(MetricsBase):
    def __init__(self, pillar: str, pillar_data: typing.Dict[str, dict], dates: typing.List[str] = None):
        super(MetricsBase, self).__init__()
        self.pillar = pillar
        self.data = pillar_data
        self.dates = dates or []
        self.bounces, self.summary = self.find_bounces()
        self.report = self.build_report()

    def __repr__(self) -> str:
        dates = f"{self.dates[0]} - {self.dates[1]}"
        output = f"{self.__class__.__name__}(pillar={self.pillar}, dates=[{dates}])"
        return output

    def find_bounces(self) -> typing.Tuple[dict, dict]:
        """
        Iterate through the defects, looking for defects with state bounces.

        :return: Tuple of
            Bounced Dictionary: dict[Project][Defect Id] = Bug Object
            Summary Dictionary: dict[Project][REWORKED|TOTAL] = int, dict[Project][REWORKED|VIOLATIONS] = list[Bug]

        """
        summary = {}
        bounced = {}
        for project in self.data[self.pillar].keys():
            defects = self.data[self.pillar][project]

            bounced[project] = {}
            summary[project] = {
                BounceMetricConstants.BOUNCED: 0,
                BounceMetricConstants.TOTAL: 0,
                BounceMetricConstants.VIOLATIONS: []}

            logging.debug(f"Number of defects found for {self.pillar}:{project}: {len(defects)}")

            for defect in defects:

                # Don't include defects that are not closed yet... more can happen, so do not report.
                # Also check to make sure CLOSED is the last/current state.
                if (BounceMetricConstants.CLOSED not in defect.states_unique_summary or
                        defect.states_unique_summary[-1] != BounceMetricConstants.CLOSED):
                    continue

                # If a defect has been updated (e.g. - comments) but did not change to the closed state within the
                # specified interval, do not include that defect in the analysis.
                interval_start_date = datetime(*[int(x) for x in self.dates[0].split(BugKeys.DATE_DELIMITER)])
                was_closed_before_interval = defect.states[-1].timestamp < interval_start_date

                logging.debug(f"Checking if defect {defect.defect_id} was closed before the start interval.")
                logging.debug(f"\tTIMESTAMP {defect.states[-1].timestamp }")
                logging.debug(f"\tINTERVAL: {interval_start_date}")
                logging.debug(f"\tPRECEDES? {was_closed_before_interval}")
                if defect.states_unique_summary[-1] == BounceMetricConstants.CLOSED and was_closed_before_interval:
                    logging.debug(f"Excluding {defect.defect_id} from analysis.")
                    continue

                # These defects have been closed at least once... so look for bounces
                summary[project][BounceMetricConstants.TOTAL] += 1
                if self.defect_bounce_count(defect) > 0:
                    summary[project][BounceMetricConstants.BOUNCED] += 1

                    # If there are more 'open' states than the SLA limit, it is a SLA violation
                    if defect.states_unique_summary.count(BounceMetricConstants.OPEN) > BounceMetricConstants.SLA_LIMIT:
                        summary[project][BounceMetricConstants.VIOLATIONS].append(defect)

                    bounced[project][defect.defect_id] = defect
                    logging.debug(f"BOUNCE FOUND: {self.pillar}:{project}:{defect.defect_id}")
                    logging.debug(f"Transition history: {defect.states_unique_summary}")

        return bounced, summary

    @staticmethod
    def defect_bounce_count(bug_obj: Bug) -> int:
        """
        Count the number of normalized, unique state transitions where there was a 'test' --> 'open' transition.

        :param bug_obj: Populated Bug obj

        :return: Count of test->open transitions; 0 = no bounces

        """
        count = 0
        transition_list = bug_obj.states_unique_summary
        num_transistions = len(transition_list) - 1

        # Need at least two state changes to have a bounce... (new bugs can't bounce)
        if num_transistions > 2:
            for index in range(num_transistions):
                current_state = transition_list[index]
                next_state = transition_list[index + 1]
                if (None not in [current_state, next_state] and
                        current_state.lower() == BounceMetricConstants.TEST and
                        next_state.lower() == BounceMetricConstants.OPEN):
                    count += 1
        return count

    def build_table(self) -> prettytable.PrettyTable:
        """
        Build a table of bounced defects.

        :return: prettyTable of tallied results

        """
        # Define column header names
        pillar = 'Pillar'
        project_name = 'Project'
        defect_id = 'Defect ID'
        sla = 'Violation'
        history = 'Transition History'

        # Define the table
        table = prettytable.PrettyTable()
        table.field_names = [pillar, project_name, defect_id, sla, history]
        table.align[history] = 'l'

        # Iterate through the data
        logging.debug(f"Bounce-back results:\n{pprint.pformat(self.bounces)}")
        for project in self.bounces.keys():
            data_row = [self.pillar, project.upper(), "No bounce backs", "", ""]
            if self.bounces[project]:
                for defect_id, defect in self.bounces[project].items():
                    violation = "*" if (defect.states_unique_summary.count(BounceMetricConstants.OPEN) >
                                        BounceMetricConstants.SLA_LIMIT) else ''
                    data_row = [self.pillar, project.upper(), defect_id, violation, defect.states_unique_summary]
                    table.add_row(data_row)
            else:
                table.add_row(data_row)
        return table

    def build_report(self) -> str:
        """
        Get the table and summarize the results.

        :return: String representation of the table and the summary

        """
        report = ("NOTE: All defects in tally have been updated within the specified range "
                  f"and have been closed at least once.\n\nSLA Limit: {BounceMetricConstants.SLA_LIMIT} "
                  f"bounces.\n\nStats")

        if self.dates:
            report += f" for {self.dates[0]} - {self.dates[1]}"
        report += ":\n"

        violations = []

        # For each product, determine the stats
        for project, data in self.summary.items():
            bounced = data[BounceMetricConstants.BOUNCED]
            total = data[BounceMetricConstants.TOTAL]
            num_violations = len(data[BounceMetricConstants.VIOLATIONS])

            # Store the defects that are violations (to be displayed at the end of the report)
            if num_violations > 0:
                violations.extend(data[BounceMetricConstants.VIOLATIONS])

            try:
                percentage = (float(bounced)/float(total)) * 100.0
            except ZeroDivisionError:
                logging.warn(f"{project} - Division by zero: {pprint.pformat(data)}")
                percentage = 0.0

            # Append results to the report
            report += (f"\t- {project.upper():<8}   Defects: {total:3}  Bounced: {bounced:2}  "
                       f"Violations: {num_violations:2}    Percent Bounced Back: {percentage:4.1f}%\n")

        # Add the results table
        report += f"\n\n{self.build_table().get_string()}\n"

        # List the defect details for all defects that violated the SLA
        report += "\nVIOLATION DETAILS:\n"
        if violations:
            for defect in violations:
                report += f"{str(defect)}\n\n"
        else:
            report += "None"

        logging.debug(f"Rework Report:\n{report}")

        return report

    def write_report(self, filename: str) -> typing.NoReturn:
        """ Display and write the results to file (be sure to include metric type in the file name). """
        logging.info(f"\n\n{'*' * 120}\n\n{self.report}\n\n")
        rpt_name = filename.format(metric="bounce")
        with open(rpt_name, "w") as FILE:
            FILE.write(f"\n{self.report}\n")
        logging.info(f"Wrote bounce report to '{rpt_name}'")
