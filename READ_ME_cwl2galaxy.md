
## cwl2galaxy
This is a tool to automate the Galaxy tool XML file creation from a CWL file ;
This tool is a Planemo command named "cwl2 galaxy" that takes few arguments :
- `--path`: path to CWl tool/worklow
- `--tool`: name of the XML tool file thaht will be created


**Example:**
`planemo cwl2galaxy --tool "test_format.xml" --path format.cwl` 
Then, you can add you XML tool with the cwl and other required files in "tools" repository in Galaxy, and add your tool in /config/tool_conf.xml in Galaxy.
Finally start it up with `sh run.sh`.
(More explanation about local instance of Galaxy here : https://galaxyproject.org/admin/get-galaxy/)

**Code:**
`planemo/planemo/commands/cwl2galaxy.py`
`planemo/planemo/tool_builder.py`
`planemo/planemo/get_command.py`

* * *


## 1. **Approaches & strategies:**


CWL input file is converted in a dictionary by **cwltool**, in order to detect special keys.
An python object "`Cwl`" is created from this dictionary, this object will contains a list of inputs and outputs  objects.
Important keys are:
- `Class`
- `Inputs`
- `Outputs`, `stdout`
- `$namespaces`, `$schemas`
- `label`, `doc`, `version`


### 1.1/ Inputs
For each input found in the `Inputs` field, an "`Input_cwl`" object is created.
Collected information:
- name
- is optional
- is array, record or enum
- `type`
- `format` (for file)
- default value
- `label`
- `doc`

**TODO:** Look for ways to include SecondaryFile.

### 1.2/ Outputs, stdout
For each output an python objest "`Output_cwl`" is created.
Others parameters than Files are not taken into account by Galaxy
Collected information:
- name
- `outputBinding/glob`
- format
- `label`
- `doc`
Galaxy outputs cannot be optional, but if an output file is not found, there is no error, it is just not in outputs.
Others outputs type can be found in the json output file.
File, stdout, Directory, array of Files/Directories or File/Directory fields from records


### 1.3/ others keys
- `$namespaces` & `$schemas` to load needed ontologies (especially for File formats) using owlready2
- `label`, `doc`, `version` to document the XML

Browse keys `$namespaces` and `$schemas` in the CWL file, in order to create a dictionary where the key is the key of the namespaces and values are both the schemas and the URL ontology.
When the system comes across a `format` key, it checks if there is an ontology namespaces that matchs with it. If so, it loads the ontology and get the label of the file format corresponding.

**TO DO:** citations & tests

* * *

## 2. Command
Fist step is the generation of job CWL file. In the command field, we will browse the inputs list and get values given by the user in order to write `job.yml`.
Then it will execute `cwltool tool.cwl job.yml`.

* * *

## 3. Tests:
planemo/tests_cwl2galaxy
