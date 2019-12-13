from dataclasses import dataclass


@dataclass
class RequestData:
    """ Headers for requests """
    CONTENT_TYPE: str = 'Content-Type'
    JSON: str = "application/json"


@dataclass
class SeverityTypes:
    """ Definitions of Severity Types """
    CRITICAL: str = 'critical'
    MAJOR: str = 'major'
    MINOR: str = 'minor'
    COSMETIC: str = 'cosmetic'


class JiraSeverities:
    """ Definition of Severity Values """
    SEVERITIES = {
        SeverityTypes.CRITICAL: 1,
        SeverityTypes.MAJOR: 2,
        SeverityTypes.MINOR: 3,
        SeverityTypes.COSMETIC: 4
    }

    @staticmethod
    def get_severity_value(sev_string: str) -> int:
        """
        Given a severity name, return the corresponding value

        :param sev_string: Name of the severity

        :return: (int) Severity value
        """
        key = (sev_string.lower().split(' '))[0]
        return JiraSeverities.SEVERITIES.get(key, sev_string)


@dataclass
class JiraFields(object):
    """ Definition of fields in the Jira JSON response body """
    KEY: str = 'key'

    ASSIGNEE: str = 'assignee'
    CHANGE_LOG: str = 'changelog'
    CHG_FROM: str = 'fromString'
    CHG_TO: str = 'toString'
    COMPONENTS: str = 'components'
    CREATED: str = 'created'
    DEFECT_ID: str = KEY
    DESCRIPTION: str = 'description'
    DETECTED: str = 'customfield_14116'
    ENVIRONMENT: str = 'environment'
    FIELD: str = 'field'
    FIELDS: str = 'fields'
    FIXED_VERSION: str = 'fixVersions'
    HISTORIES: str = 'histories'
    ISSUES: str = 'issues'
    ISSUETYPE: str = 'issuetype'
    ITEMS: str = 'items'
    LABELS: str = 'labels'
    LINK: str = 'self'
    NAME: str = 'name'
    PRIORITY: str = 'priority'
    PROJECT: str = 'project'
    REPORTER: str = 'creator'
    SEVERITY: str = 'customfield_13654'
    STATUS: str = 'status'
    SUMMARY: str = 'summary'
    VALUE: str = 'value'
