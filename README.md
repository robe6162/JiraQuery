# JiraMetrics

The purpose of this application is to query and pull defect information from Jira to generate metrics that cannot be easily exposed within Jira.

## Usage

```
usage: metrics.py [-h] [-u USER] [-p PSWD] [-c CFG] [-r [PILLAR [PILLAR ...]]]
                  [-s START] [-e END] [-l] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -u USER, --user USER  REQUIRED: Jira Login Username; SSO Username; if not
                        provided, use environ var 'SSO_USER'. NOTE: CLI gets
                        priority over the envvars.
  -p PSWD, --pswd PSWD  REQUIRED: Jira Login Password; SSO Password; if not
                        provided, use environ var 'SSO_PASS'. NOTE: CLI gets
                        priority over the envvars.
  -c CFG, --cfg CFG     REQUIRED: Config file to use
  -r [PILLAR [PILLAR ...]], --pillar [PILLAR [PILLAR ...]]
                        REQUIRED: Name of pillar; must be defined in the
                        config file, or 'ALL' for all pillars
  -s START, --start START
                        REQUIRED: Start Date Range: YYYY-MM-DD
  -e END, --end END     REQUIRED: End Date Range: YYYY-MM-DD
  -l, --list            List all defined pillars and projects
  -d, --debug           Enable debug logging
```

All parameters are required for execution except *--help, --debug, --list*.

Example: 

     ./metrics.py -u <username> -p <pswd> -c mappings.yaml -r ERP -s 2019-09-01 -e 2019-09-30

Note: If *--list* is provided, it will list all pillars and projects and then exit without executing any queries.

**Environment Variables**:

Either (or both) the SSO username and password can be set via the environment variables to avoid the values being printed on the CLI.

    export SSO_USER="<user_name>"
    export SSO_PASS="<password>"

To execute using the environment variables, do not include the corresponding arguments on the CLI:

     ./metrics.py -c mappings.yaml -r ERP -s 2019-09-01 -e 2019-09-30

**NOTE:** If the values are set in the environment and on the CLI, **the CLI will get precedence** over the environment variables.


## Installation

> It is recommended to create a virtual environment for this project.

* Clone the project into the virtual environment.
* Activate the virtual environment.
* Navigate to the source directory that contains `setup.py`. - the base directory of the cloned repo.
* Install the project: `pip install .` - This will use setup.py to install the project and it's pypi dependencies.
* **BOOM!** -> Execute the script...

# General Guidelines
* Requires python 3.7+.
* All methods should use the `typing` module to declare parameter types and return types.
* Docstrings should be included for all implemented non-"\_\_\<method_name>\_\_" methods.
* PEP-8 line length is set to 120 (rather than the standard 79 characters).

## Data Processing
Given a valid pillar of Jira projects and a specific date range, the script will query each Jira project for defects **updated** within the date range. Then for each inidividual defect listed in the response, the script will query Jira for the detailed defect information & history. All of the defect information is serialized into a _Bug_ model object and stored in a list. (See "Code Organization" below for an explanation of the architecture and classes).

The list of _Bug_ objects is then passed to the various metric generators to calculate and report the metrics. Currently, there is only a single metric generator implemented: BounceMetrics.

## Output
The application will create 2+ files:
* Log file:  `defects.<START_DATE>.<END_DATE>.log`
* One report file **per metric type**: `defects.<PILLAR>.<START_DATE>.<END_DATE>.<MetricType>.report`

The files will be created in the same directory as the execution directory.

## Code Organization
```
<base_directory> 
  |
  + <config>  -> Command Line processing and config file parsing modules.
  |
  + <defect_models> --> Jira data serialization model
  |
  + <jira_client> --> Connection Client for Jira
  | 
  + <logging> --> Logging facility
  |
  + <metrics> --> Metric generation from serialized Jira response data
```

**base_directory** - the location of the primary application file: `metrics.py`. The other required files are also found here: 
* setup.py (used for installation of the application and dependencies), 
* README.md (_this file_), and 
* _mappings.yaml_ (the pillar/project configuration file). 

**config**
* _cfg_mappings.py_ - Defines YamlFile parsing and config storage classes. The supported config file format is YAML (see mappings.yaml for an example). The YAML keywords are explicitly defined in *YamlKeywords*; this provides a single defintion for the expected/allowed keywords. If additional YAML fields are added, *YamlKeyWords*, *YamlFile*, and *ConfigFileType* classes need to be updated.

   > NOTE: The *ConfigFileType* class was implemented as a base (virtual) class to allow consistent support of different config file formats, although currently, only YAML files are supported.

* _command_line.py_ - Defines all supported command line options. (See python's *ArgParse* module for implementation details). 

**defect_models**
* _bug_model.py_ - Defines the object representation of a defect. There are 3 classes defined in this module:
  * *BugKeys* - A data class that defines keyword constants used to instantiate and reference data in the *Bug* class. If additional attributes are added to the *Bug* class, the attribute names need to be defined in the *BugKeys* class so the *Bug* object can be instantiated and attributes referenced via dictionary. 

  * *RequiredFields* - A data class that defines the required fields in a defect. These are typically used to filter the defect data set to a specific subset of defects.

  * *Bug* - The primary defect serialization object. All object attributes should be prefaced with a `_` and the corresponding name should be defined in the *BugKeys* class. 
  
  e.g. -
  
  **attribute name**: \_attribute_1  
  **referenced name**: attribute_1. 
  
  If the additional attribute should also be exposed when displaying the instance (printing the object or casting to a string: e.g - str(_Bug_), the attribute should be included in the _Bug.reportable_attributes_list_, and the `__str__()` method updated to include the attribute description and name.

**jira_client**
* _jira_mappings.py_ - This is a series of classes that define various fields found in the Jira query, Jira response, and enumerations of specific data fields (e.g. - severity). This provides a single definition, so if field names change, it can be globally updated in a single location.

* _jira_client.py_ - This contains the code for querying Jira, serializing the response, and requesting additional detail for defects.

  > **NOTE**: This class violates the common practice that clients should only transmit and receive data; clients do not process data. This class will serialize the data and return a processed response. This was done for convenience and speed of development, but restricts the client to this specific implementation.

  * _DefectKeys_: A data class for tracking data structure keys within the serialization process.
  
  * _JiraClient_: The actual client; builds a query based on the provided input, uses `requests` to retrieve the data. The defect is serialized into a _Bug_ object, data specific to the defect (change_log) is queried and included in the Bug object. All states are also normalized to basic superset of states to simplify complex state flows, allowing comparison and common state transitions between projects. The superset of states is defined in the YAML file, but is typically _new_, _open_, _test_, _closed_.
  
  The primary method is `JiraClient.query(<args>)` which returns a _Bugs_ object (a list implementation containing a list of instantiated and populated Bug objects).
  
**logging**
* _logger.py_ - a customized implementation of logger to provide explicit data about the log message:
   * the timestamp,
   * the process id (pid),
   * the level (FATAL, CRITICAL, WARN, INFO, DEBUG),
   * the subsystem logging,
   * filename & line number in the source code,
   * the msg.
   
   **Example:** `[100319-14:52:59] - [WARNING] - [19760][src.defects.defect_metrics.jira_client:_decompose_bug_entry|261] - Did not find: assignee`
   
   To use in module, instantiate this logger at the top of the file. 
   
   > logging = logger.Logger()
   
   and when logging in your module level code: `logging.info(msg)`
   
   
   To use in the primary application (main()):
   > logging_level = logger.Logger.STR_TO_VAL\['debug' if cli_args.args.debug else 'info']
   > logging = logger.Logger(default_level=logging_level, filename=logfile, project="defect_metrics")
    
   This will set up all modules correctly and instantiate the loggers accordingly.
   
   When logging in your application level code: `logging.info(msg)`
    
**metrics** - Each metric generation module should be stored here.
The module should take a list of data objects (e.g. - _Bug_ objects), filter, accumulate, tally the results, and generate the report when instantiated. 
* _Methods and Requirements_: The metrics calculation and implementation is metric specific, but inherit from `metrics.metrics_base.MetricsBase` and should adhere to the following:
  * `class.report` should contain the report
  * `class.__str__()` should return the contents of `class.report`. 
  * The class should implement `build_report` whcih returns a string representation of the report.
  * The class should implement `write_report` to log the report and write the report to file.
  
