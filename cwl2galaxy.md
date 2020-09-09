This is a tool to automate the Galaxy tool XML file creation from a CWL file ;
This tool is a Planemo command named "cwl2 galaxy" that takes few arguments :
- `--force`: to force the creation (overwrite) of the XML tool
- `--path`: path to CWl tool/worklow
- `--tool`: name of the XML tool file thaht will be created

**Approaches & strategies:**


### 1. CWL input file 
CWL input file is converted in a python dictionary, in order to detect special keys.
An python object "`Cwl`" is created from this dictionary.
Important keys are:
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

**TO DO:** Verify uses case of array of arrays or records of records are taken into account. 
Look for ways to include SecondaryFile.

### 1.2/ Outputs, stdout
For each output an python objest "`Output_cwl`" is created.
Others parameters than Files are not taken into account by Galaxy
Collected information:
- name
- `glob`
- `label`
- `doc`
Galaxy outputs cannot be optional, but if an output file is not found, there is no error, it is just not in outputs.
Others outputs type can be found in the json output file.

**TO DO:** only name and type are given in the Output field in CWL workflows, so for output data it only gives the type, not the name or the format of the file.


### 1.3/ others keys
- `$namespaces` & `$schemas` to load needed ontologies (especially for File formats) using owlready2
- `label`, `doc`, `version` to document the XML

Browse key `$namespaces` and `$schemas` in the CWL file, in order to create a dictionnary where the key is the key of the namespaces and values are both the schemas and the ontology URL.
When the system comes across a `format` key, it checks if there is an ontology namespaces that matchs with it. If so, it loads the ontology and get the label of the file format corresponding.

**TO DO:** citations & tests

### 2. Command
Fist step is the generation of job CWL file. In the command field, we will browse the inputs list and get values given by the user in order to write `job.yml`.
Then it will execute `cwltool tool.cwl job.yml`.




