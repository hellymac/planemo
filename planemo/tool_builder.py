"""This module contains :func:`build` to build tool descriptions.

This class is used by the `tool_init` command and can be used to build
Galaxy and CWL tool descriptions.
"""

import os
import re
import fnmatch
import shlex
import shutil
import subprocess
from collections import namedtuple

from planemo import io
from planemo import templates
from planemo import get_command
from owlready2 import *
#from galaxy.lib.galaxy.tool_util.cwl import representation

REUSING_MACROS_MESSAGE = ("Macros file macros.xml already exists, assuming "
                          " it has relevant planemo-generated definitions.")
DEFAULT_CWL_VERSION = "v1.0"


TOOL_TEMPLATE = """<tool id="{{id}}" name="{{name}}" version="{{version}}" python_template_version="3.5">
{%- if description %}
    <description>{{ description }}</description>
{%- endif %}
{%- if macros %}
    <macros>
        <import>macros.xml</import>
    </macros>
    <expand macro="requirements" />
{%- if version_command %}
    <expand macro="version_command" />
{%- endif %}
{%- else %}
    <requirements>
{%- for requirement in requirements %}
        {{ requirement }}
{%- endfor %}
{%- for container in containers %}
        {{ container }}
{%- endfor %}
    </requirements>
{%- if version_command %}
    <version_command>{{ version_command }}</version_command>
{%- endif %}
{%- endif %}
    <command detect_errors="exit_code"><![CDATA[
{%- if command %}
        {{ command }}
{%- else %}
        TODO: Fill in command template.
{%- endif %}
    ]]></command>
    <inputs>
{%- for input in inputs %}
        {{ input }}
{%- endfor %}
    </inputs>
    <outputs>
{%- for output in outputs %}
        {{ output }}
{%- endfor %}
    </outputs>
{%- if tests %}
    <tests>
{%- for test in tests %}
        <test>
{%- for param in test.params %}
            <param name="{{ param[0]}}" value="{{ param[1] }}"/>
{%- endfor %}
{%- for output in test.outputs %}
            <output name="{{ output[0] }}" file="{{ output[1] }}"/>
{%- endfor %}
        </test>
{%- endfor %}
    </tests>
{%- endif %}
    <help><![CDATA[
{%- if help %}
        {{ help }}
{%- else %}
        TODO: Fill in help.
{%- endif %}
    ]]></help>
{%- if macros %}
    <expand macro="citations" />
{%- else %}
{%- if doi or bibtex_citations %}
    <citations>
{%- for single_doi in doi %}
        <citation type="doi">{{ single_doi }}</citation>
{%- endfor %}
{%- for bibtex_citation in bibtex_citations %}
        <citation type="bibtex">{{ bibtex_citation }}</citation>
{%- endfor %}
    </citations>
{%- endif %}
{%- endif %}
</tool>
"""

MACROS_TEMPLATE = """<macros>
    <xml name="requirements">
        <requirements>
{%- for requirement in requirements %}
        {{ requirement }}
{%- endfor %}
            <yield/>
{%- for container in containers %}
        {{ container }}
{%- endfor %}
        </requirements>
    </xml>
    <xml name="citations">
        <citations>
{%- for single_doi in doi %}
            <citation type="doi">{{ single_doi }}</citation>
{%- endfor %}
{%- for bibtex_citation in bibtex_citations %}
            <citation type="bibtex">{{ bibtex_citation }}</citation>
{%- endfor %}
            <yield />
        </citations>
    </xml>
{%- if version_command %}
    <xml name="version_command">
        <version_command>{{ version_command }}</version_command>
    </xml>
{%- endif %}
</macros>
"""

CWL_TEMPLATE = """#!/usr/bin/env cwl-runner
cwlVersion: '{{cwl_version}}'
class: CommandLineTool
id: "{{id}}"
label: "{{label}}"
{%- if containers or requirements %}
hints:
{%- for container in containers %}
  DockerRequirement:
    dockerPull: {{ container.image_id }}
{%- endfor %}
{%- if requirements %}
  SoftwareRequirement:
    packages:
{%- for requirement in requirements %}
    - package: {{ requirement.name }}
{%- if requirement.version %}
      version:
      - "{{ requirement.version }}"
{%- else %}
      version: []
{%- endif %}
{%- endfor %}
{%- endif %}
{%- endif %}
{%- if inputs or outputs %}
inputs:
{%- for input in inputs %}
  {{ input.id }}:
    type: {{ input.type }}
    doc: |
      TODO
    inputBinding:
      position: {{ input.position }}
{%- if input.prefix %}
      prefix: "{{input.prefix.prefix}}"
{%- if not input.prefix.separated %}
      separate: false
{%- endif %}
{%- endif %}
{%- endfor %}
{%- for output in outputs %}
{%- if output.require_filename %}
  {{ output.id }}:
    type: string
    doc: |
      Filename for output {{ output.id }}
    inputBinding:
      position: {{ output.position }}
{%- if output.prefix %}
      prefix: "{{output.prefix.prefix}}"
{%- if not output.prefix.separated %}
      separate: false
{%- endif %}
{%- endif %}
{%- endif %}
{%- endfor %}
{%- else %}
inputs: [] # TODO
{%- endif %}
{%- if outputs %}
outputs:
{%- for output in outputs %}
  {{ output.id }}:
    type: File
    outputBinding:
      glob: {{ output.glob }}
{%- endfor %}
{%- else %}
outputs: [] # TODO
{%- endif %}
{%- if base_command %}
baseCommand:
{%- for base_command_part in base_command %}
  - "{{ base_command_part}}"
{%- endfor %}
{%- else %}
baseCommand: []
{%- endif %}
{%- if arguments %}
arguments:
{%- for argument in arguments %}
  - valueFrom: "{{ argument.value }}"
    position: {{ argument.position }}
{%- if argument.prefix %}
      prefix: "{{argument.prefix.prefix}}"
{%- if not argument.prefix.separated %}
      separate: false
{%- endif %}
{%- endif %}
{%- endfor %}
{%- else %}
arguments: []
{%- endif %}
{%- if stdout %}
stdout: {{ stdout }}
{%- endif %}
doc: |
{%- if help %}
  {{ help|indent(2) }}
{%- else %}
   TODO: Fill in description.
{%- endif %}
"""

CWL_TEST_TEMPLATE = """
- doc: test generated from example command
  job: {{ job_filename }}
{%- if outputs %}
  outputs:
{%- for output in outputs %}
    {{ output.id }}:
      path: test-data/{{ output.example_value }}
{%- endfor %}
{%- else %}
  outputs: TODO
{%- endif %}
"""

CWL_JOB_TEMPLATE = """
{%- if inputs %}
{%- for input in inputs %}
{%- if input.type == "File" %}
{{ input.id }}:
  class: File
  path: test-data/{{ input.example_value }}
{%- else %}
  {{ input.id }}: {{ input.example_value }}
{%- endif %}
{%- endfor %}
{%- else %}
# TODO: Specify job input.
{}
{%- endif %}
"""


def build(**kwds):
    """Build up a :func:`ToolDescription` from supplid arguments."""
    if kwds.get("cwl"):
        builder = _build_cwl
    else:
        builder = _build_galaxy
    return builder(**kwds)


def _build_cwl(**kwds):
    _handle_help(kwds)
    _handle_requirements(kwds)
    assert len(kwds["containers"]) <= 1, kwds
    command_io = CommandIO(**kwds)
    render_kwds = {
        "cwl_version": DEFAULT_CWL_VERSION,
        "help": kwds.get("help", ""),
        "containers": kwds.get("containers", []),
        "requirements": kwds.get("requirements", []),
        "id": kwds.get("id"),
        "label": kwds.get("name"),
    }
    render_kwds.update(command_io.cwl_properties())

    contents = _render(render_kwds, template_str=CWL_TEMPLATE)
    tool_files = []
    test_files = []
    if kwds["test_case"]:
        sep = "-" if "-" in kwds.get("id") else "_"
        tests_path = "%s%stests.yml" % (kwds.get("id"), sep)
        job_path = "%s%sjob.yml" % (kwds.get("id"), sep)
        render_kwds["job_filename"] = job_path
        test_contents = _render(render_kwds, template_str=CWL_TEST_TEMPLATE)
        job_contents = _render(render_kwds, template_str=CWL_JOB_TEMPLATE)
        tool_files.append(ToolFile(tests_path, test_contents, "test"))
        tool_files.append(ToolFile(job_path, job_contents, "job"))
        for cwl_input in render_kwds["inputs"] or []:
            if cwl_input.type == "File" and cwl_input.example_value:
                test_files.append(cwl_input.example_value)

        for cwl_output in render_kwds["outputs"] or []:
            if cwl_output.example_value:
                test_files.append(cwl_output.example_value)

    return ToolDescription(
        contents,
        tool_files=tool_files,
        test_files=test_files
    )


def _build_galaxy(**kwds):
    # Test case to build up from supplied inputs and outputs, ultimately
    # ignored unless kwds["test_case"] is truthy.

    _handle_help(kwds)

    # process raw cite urls
    cite_urls = kwds.get("cite_url", [])
    del kwds["cite_url"]
    citations = list(map(UrlCitation, cite_urls))
    kwds["bibtex_citations"] = citations

    # handle requirements and containers
    _handle_requirements(kwds)

    command_io = CommandIO(**kwds)
    kwds["inputs"] = command_io.inputs
    kwds["outputs"] = command_io.outputs
    kwds["command"] = command_io.cheetah_template

    test_case = command_io.test_case()

    # finally wrap up tests
    tests, test_files = _handle_tests(kwds, test_case)
    kwds["tests"] = tests

    # Render tool content from template.
    contents = _render(kwds)

    tool_files = []
    append_macro_file(tool_files, kwds)

    return ToolDescription(
        contents,
        tool_files=tool_files,
        test_files=test_files
    )

###############  CWL 2 GALAXY  ####################

def write_command(inputs, id):
    """ write the tool XML command : create cwl job file """
    command = ""
    for i in inputs:
        # command += input_to_yaml(i)
        command += get_command.get_command(i)
    command +="\ncwltool '$__tool_directory__/" + id + "\' $job_gal >> $stdout_gal"
    return command

def build_cwl2galaxy(file, filename, **kwds):
    tool = Cwl(file)
    kwds["tool"] = kwds.get("tool")
    kwds["id"] = tool.name
    kwds["name"] = tool.label
    kwds["command"] = write_command(tool.inputs, tool.name) 
    kwds["requirements"] = [] # objet requirement
    kwds["help"] = tool.help
    kwds["inputs"] = tool.inputs
    kwds["outputs"] = ['   <data name="job_gal" format="json" label="parameters" from_work_dir= "job_gal.yml"/>', '   <data name="stdout_gal" format="json" label="outputs list" from_work_dir="stdout_gal.json" />']
    for o in tool.outputs:
        if o.type == "File" or o.type == "Directory":
            kwds["outputs"].append(o)
    kwds["macros"] = None 
    kwds["tests"] = []
    kwds["test_case"] = None
    kwds["version"] = tool.version

    contents = _render(kwds)
    tool_files = []
    test_files = None
    
    return ToolDescription(
        contents,
        tool_files=tool_files,
        test_files=test_files
    )

def write_tool(ctx, tool_description, **kwds):
    """Write a tool description to the file system guided by supplied CLI kwds."""
    output = kwds.get("tool")
    if not io.can_write_to_path(output, **kwds):
        ctx.exit(1)

    io.write_file(output, tool_description.contents)
    io.info("Tool written to %s" % output)

class Cwl:
    def __init__(self, tool):
        dict = tool.tool
        self.dict = dict
        self.ontology = {}
        self.cwlclass = dict["class"]
        self.requirements = tool.requirements
        self.workflow = False

        if self.dict["class"] == "Workflow" :
            self.workflow = True
        if "id" in dict:
            self.name = dict["id"].split("/")[-1].split("#")[0]
        else:
            self.name = "tool.cwl"
        if "label" in dict:
            self.label = dict["label"]
        else :
            self.label = dict["id"].split("/")[-1].split("#")[-1]
        if "doc" in dict:
            self.help = dict["doc"]
        else:
            self.help = None
        if "version" in dict:
            self.version = dict["version"]
        else:
            self.version = "0.1.0"
        if "stdout" in dict:
            self.stdout = dict["stdout"]
        else:
            self.stdout = None

        if "$namespaces" in dict:
            iterator = 0
            for owl in dict["$namespaces"]:
                self.ontology[owl]= dict["$schemas"][iterator], dict["$namespaces"][owl]
                iterator = iterator + 1
             
        self.nbinputs = len(dict["inputs"])
        self.inputs = []
    
        if isinstance(self.dict["inputs"], list) :
            #handle syntax " - id: param_name" :
            for i in range(self.nbinputs):
                self.inputs.append(Input_cwl(self.dict["inputs"][i], self.dict["inputs"][i]["id"], self.ontology))
        else:
            for input in self.dict['inputs']:
                self.inputs.append(Input_cwl(self.dict['inputs'][input], input, self.ontology))


        self.nboutputs = len(dict["outputs"])
        self.outputs = []

        if self.cwlclass == "Workflow":
            if isinstance(self.dict["outputs"], list) :
                for i in range(self.nboutputs):
                    self.outputs.append(Output_cwl(self.dict["outputs"][i], self.workflow, self.dict["outputs"][i]["id"].split("#")[-1],
                    self.stdout, self.requirements, self.ontology, tool.steps))
            else:
                for output in self.dict['outputs']:
                    self.outputs.append(Output_cwl(self.dict['outputs'][output], self.workflow, output.split("#")[-1], self.stdout,
                    self.requirements, self.ontology, tool.steps))  

        else:
            if isinstance(self.dict["outputs"], list) :
                for i in range(self.nboutputs):
                    self.outputs.append(Output_cwl(self.dict["outputs"][i], self.workflow ,self.dict["outputs"][i]["id"].split("#")[-1], 
                     self.stdout, self.requirements, self.ontology))
            else:
                for output in self.dict['outputs']:
                    self.outputs.append(Output_cwl(self.dict['outputs'][output], self.workflow, output.split("#")[-1], self.stdout, 
                    self.requirements, self.ontology))  


        # sys.exit()

class Input_cwl(object):

    def __init__(self, dict_in, name, ontology):
        self.name = name.split("#")[-1].split("/")[-1]
        self.source = name.split("#")[-1]
        self.optional = False
        self.multiple = False
        self.array_input = None
        self.record_inputs = []
        self.enum_options = []
        self.type = None

        def fill_input_dict(dictionnary):
            self.type = dictionnary["type"]
            if self.type == "array" and isinstance(dictionnary["items"], str):
                if dictionnary["items"] == "File" or dictionnary["items"] == "enum":
                    self.multiple = True
                    self.type = dictionnary["items"]
                else :
                    d = dict()
                    d["type"] = dictionnary["items"]
                    d["name"] = self.source 
                    self.array_input = Input_cwl(d, "array_" + self.source, ontology)
            
            elif self.type == "array" and (dictionnary["items"]["type"] == "File" or dictionnary["items"]["type"] == "enum"):
                self.multiple = True
                self.type = dictionnary["items"]["type"]
                if "format" in dictionnary["items"]:
                    self.format = dictionnary["items"]["format"]

            elif self.type == "array" and isinstance(dictionnary["items"], dict):
                if "name" in dictionnary["items"]:
                    self.array_input = Input_cwl(dictionnary["items"], dictionnary["items"]["name"].split("/")[-1], ontology)
                else:
                    self.array_input = Input_cwl(dictionnary["items"], "array_" + self.source, ontology)
                
            elif self.type == "enum":
                # if isinstance(dictionnary["symbols"],list):
                #     for option 
                #     self.enum_options = dictionnary["symbols"]
                # else:
                for option in dictionnary["symbols"]:
                    self.enum_options.append(option.split('#')[-1].split('/')[-1])

            elif self.type == "record":
                for element in dictionnary["fields"]:
                    self.record_inputs.append(Input_cwl(element, element['name'].split("/")[-1], ontology))

            self.type = CWL_TO_GALAXY_TYPES[self.type]

        if "label" in dict_in:
            self.label = dict_in["label"]
        else :
            self.label = self.name
                
        if "default" in dict_in:
            self.value = dict_in["default"]
        else :
            self.value = None
                
        if "doc" in dict_in:
            self.doc = dict_in["doc"]  
        else :
            self.doc = None
                
        if "format" in dict_in:
            self.format = dict_in["format"]  
            for owl in ontology:
                if self.format.split(":")[0] == owl :
                    ont = get_ontology(ontology[owl][0]).load()
                    tag = str(self.format.split(":")[1])
                    self.format = ont.search(iri = str(ontology[owl][1])+tag)[0].label[0]

                if str(ontology[owl][1]) in str(dict_in["format"]):
                    ont = get_ontology(ontology[owl][0]).load()
                    tag = str(self.format.split("/")[-1])
                    self.format = ont.search(iri = str(ontology[owl][1])+tag)[0].label[0]
        else:
            self.format = None

        if isinstance(dict_in["type"], str):
            fill_input_dict(dict_in)
        
        if isinstance(dict_in["type"], list): #CommebntedSeq
            if ('null' in dict_in["type"]):
                self.optional = True
                dict_in["type"].remove('null')

            if len(dict_in["type"]) == 1:
                if isinstance(dict_in["type"][0], str):
                    dict_in["type"] = dict_in["type"][0]
                    fill_input_dict(dict_in)
                else:
                    if isinstance(dict_in["type"][0]["type"], str):
                        fill_input_dict(dict_in["type"][0]) #ou [0]["type"]??
                    if isinstance(dict_in["type"][0]["type"], dict):
                        fill_input_dict(dict_in["type"][0]["type"])
                # can it be a list ?
            else:
                raise Exception("Too many types for this input")
 
        if isinstance(dict_in["type"], dict): #commentedMap
            fill_input_dict(dict_in["type"])

    def __str__(self):
        result = ""
        template = '<param type="{0}" name="{1}" label="{2}" optional="{3}"'
        
        if self.value != None :
            template+=' value="{4}"'
        
        if self.doc != None :
            template+= ' help="{5}"'
        
        if self.format != None :
            template+=' format="{6}"' #format only if type is data
        
        if self.multiple:
            template += ' multiple=\"true\"'
        
        if not self.type == "select":
            template+='/>'
        
        if self.type == "data": 
                result += "          " + template.format(self.type, self.name, self.label, self.optional, self.value, self.doc, self.format) + "\n"
  
        elif self.type == "repeat": 
            result += "<repeat name=\'" + self.name + "\' title=\'" + self.name +"\' > \n"
            result += str(self.array_input)
            result += "</repeat> \n"
 
        elif self.type == "section":
            result = "<section name=\'" + self.name + "\' title= \'" + self.name + "\' expanded=\"True\"> \n"
            for i in self.record_inputs:
                result += "            " + str(i) + "\n"
            result += "</section> \n"
            
        elif self.type == "select":
            result +=  template.format(self.type, self.name, self.label, self.optional, self.value, self.doc, self.format)+">"
            for option in self.enum_options:
                result += '\n      <option value= "' + option + '" >' + option + "</option>"
            result += "\n        </param>"

        elif self.format == "data_collecion":
            result += "<param name=\"" + self.name + " type=\"data_collection\" collection_type=\"list\" label=\""+ self.label +"\" />"
        else:
            result += template.format(self.type, self.name, self.label, self.optional, self.value, self.doc, self.format)
        return(result)
        
class Output_cwl(object):

    def __init__(self, output, workflow, name, stdout, requirements, ontology, *args):
        self.name = name.split("#")[-1].split("/")[-1]
        self.source = name.split('#')[-1]
        self.record_outputs = []
        self.array = False
        self.record = False
        self.array_output = None
        self.type = None
        self.doc = ""
        self.default = None
        self.format = None
        self.from_path = None

        def _wf_get_glob(id_out, steps):
            """ return glob field from the step """
            if isinstance(id_out, list):
                id_out = id_out[0]
            for step in steps:
                for out in step.tool["outputs"]:
                    if out["id"] == id_out :
                        self.from_path = out["outputBinding"]["glob"]
                        if self.doc == None and "doc" in out:
                            self.doc = out["doc"]
                        if self.format == None and "format" in out:
                            self.format = out["format"]
                        if self.default == None and "default" in out:
                            self.default = out["default"]

        def set_type(dictionnary):
            self.type = dictionnary["type"]      
            if self.type == "array": 
                if isinstance(dictionnary["items"],str):
                    if dictionnary["items"] == "File" or dictionnary["items"] == "Directory":
                        self.array = True
                        self.type = dictionnary["items"]

                elif isinstance(dictionnary["items"], dict):
                    self.array = True
                    if "name" in dictionnary["items"]:
                        self.array_output = Output_cwl(dictionnary["items"], workflow, dictionnary["items"]["name"], stdout, requirements, ontology, args[0])
                    # else:
                    #     self.array_output = Output_cwl(output=dictionnary["items"],workflow,name="array_" + self.source, stdout, requirements, ontology, args)
                    # if dictionnary["items"]["type"]=="array":
                    #     self.array = True
                    #     if if dictionnary["items"]["items"] == "File" or dictionnary["items"] == "Directory":
                    # #     print("todo")
                    # elif dictionnary["items"]["type"]=="record":
                    #     print("todo") 
            elif self.type == "record":
                for field in output["fields"]:
                    self.record_outputs.append(Output_cwl(field, workflow, self.name, stdout, requirements, ontology, args[0]))

        if "label" in output:
            self.label = output["label"]
        else:
            self.label = self.name

        if "doc" in output:
            self.doc = output["doc"]  

        if "format" in output:
            self.format = output["format"]

        if "outputBinding" in output and "glob" in output["outputBinding"]:
            self.from_path = output["outputBinding"]["glob"]

        if "outputSource" in output and workflow:
            _wf_get_glob(output["outputSource"], args[0])


        if isinstance(output["type"], str):
            set_type(output)

        elif isinstance(output["type"], dict):
            set_type(output["type"])
        
        elif isinstance(output["type"], list):
            if 'null' in output["type"]:
                output["type"].remove("null")

            if len(output["type"]) == 1:
                if isinstance(output["type"][0], str):
                    output["type"] = output["type"][0]
                    set_type(output)
                else:
                    if isinstance(output["type"][0]["type"], str):
                        set_type(output["type"][0]) #ou [0]["type"]??
                    if isinstance(output["type"][0]["type"], dict):
                        set_type(output["type"][0]["type"])                        
        else:
            raise Exception("Too many types for this output")
        
    def __str__(self):
        template = ""
        if self.type == "record":
            template += '<collection name=\"' + self.name + '\" type=\"list\" >\n'
            for o in self.record_outputs :
                template += str(o)
            template += "</collection>"
        elif self.type == "File":
            if self.array:
                template += '<collection name= \"' + self.name + '\" type=\"list\" label=\"' + self.label + self.doc + '\"> \n'
                self.from_path += '*' # handle scatter mode
            else:
                template += '<data name=\"' + self.name + '\" label=\"' + self.label + self.doc + '\" '
                if self.format:
                    template += 'format=\"' + self.format +'\"'+ '>'
                else:
                    template += 'auto_format=\"true\"> \n'

            if len(self.from_path.split("/"))<1 :
                l = fnmatch.translate(self.from_path) 
                pattern = l[0:2]+"P&lt;designation&gt;"+l[4::] # in order to match galaxy pattern
                template += '<discover_datasets pattern=\"'+ pattern + '\" visible=\"true\" /> \n' 

            else:
                l = fnmatch.translate(self.from_path.split("/")[-1])
                pattern = l[0:2]+"P&lt;designation&gt;"+l[4::] # in order to match galaxy pattern
                template += '<discover_datasets pattern=\"' + pattern  + '\" directory=\"'    
                template += str(self.from_path)[:-(len(self.from_path.split("/")[-1]))] + '\" visible=\"true\" /> \n' 

            if self.array:
                template += '</collection>'
            else:
                template += '</data>'
        
        elif self.type == "Directory":
            if self.array :
                template += '<collection name= \"' + self.name + '\" type=\"list:list\" label=\"' + self.label + '\"> \n'
                template += '<discover_datasets pattern=\"__designation__\" directory=\"' + self.from_path + '\" visible=\"false\" /> \n' 
                template += '</collection>'
            else:
                template += '<collection name=\"' + self.name + '\" type=\"list\" label=\"' + self.label + '\"> \n'
                template += '<discover_datasets pattern=\"__designation__\" directory=\"' + self.from_path + '\" visible=\"false\" /> \n' 
                template += '</collection>'
        elif self.array:
            if self.array_output:
                if self.array_output.type == "File":
                    template += '<collection name= \"' + self.name + '\" type=\"list:list\" label=\"' + self.label + '\"> \n'
                    if len(self.array_output.from_path.split("/"))<1 :
                        l = fnmatch.translate(self.array_output.from_path+"*") 
                        pattern = l[0:2]+"P&lt;designation&gt;"+l[4::] # in order to match galaxy pattern
                        template += '<discover_datasets pattern=\"'+ pattern + '\" visible=\"true\" /> \n' 

                    else:
                        l = fnmatch.translate(self.array_output.from_path.split("/")[-1]+"*")
                        pattern = l[0:2]+"P&lt;designation&gt;"+l[4::] # in order to match galaxy pattern
                        template += '<discover_datasets pattern=\"' + pattern  + '\" directory=\"'    
                        template += str(self.array_output.from_path)[0:len(self.array_output.from_path.split("/")[-1])]
                        template += '</collection>'
                elif self.array_output.type == "Directory":
                    template += '<collection name= \"' + self.name + '\" type=\"list:list\" label=\"' + self.label + '\"> \n'
                    template += '<discover_datasets pattern=\"__designation__\" directory=\"' + self.from_path + '\" visible=\"false\" /> \n' 
                    template += '</collection>'

                elif self.array_output.type == "record":
                    template += '<collection name= \"' + self.name + '\" type=\"list:list\" label=\"' + self.label + '\"> \n'
                    for o in self.array_output.record_outputs:
                        template += str(o)
                    template += '</collection>'

        return template

SIMPLE_TYPES = ["File", "Directory", "stdout", "boolean", "int", "long", "double", "string", "Any"]
SIMPLE_TYPES_GALAXY = ["data", "data_collection", "boolean", "integer", "float", "field", "text"]
CWL_TO_GALAXY_TYPES = {
    "string": "text",
    "int": "integer",
    "File": "data",
    "boolean": "boolean",
    "enum": "select",
    "double": "float",
    "long": "integer",
    "float": "float",
    "Directory": "data_collection",
    "Any": "field",
    "array": "repeat",
    "null": "null",
    "record": "section",
    "stdout": "data",
    "record_of_records": "repeat"
    }

CWL_TO_GALAXY_OUTPUT_TYPES = {
    "File": "discover_datasets",
    "Directory": "collection"
}

###############  CWL 2 GALAXY  #################### 


def append_macro_file(tool_files, kwds):
    macro_contents = None
    if kwds["macros"]:
        macro_contents = _render(kwds, MACROS_TEMPLATE)

        macros_file = "macros.xml"
        if not os.path.exists(macros_file):
            tool_files.append(ToolFile(macros_file, macro_contents, "macros"))

        io.info(REUSING_MACROS_MESSAGE)


class CommandIO(object):

    def __init__(self, **kwds):
        command = _find_command(kwds)
        cheetah_template = command

        # process raw inputs
        inputs = kwds.pop("input", [])
        inputs = list(map(Input, inputs or []))

        # alternatively process example inputs
        example_inputs = kwds.pop("example_input", [])
        for i, input_file in enumerate(example_inputs or []):
            name = "input%d" % (i + 1)
            inputs.append(Input(input_file, name=name, example=True))
            cheetah_template = _replace_file_in_command(cheetah_template, input_file, name)

        # handle raw outputs (from_work_dir ones) as well as named_outputs
        outputs = kwds.pop("output", [])
        outputs = list(map(Output, outputs or []))

        named_outputs = kwds.pop("named_output", [])
        for named_output in (named_outputs or []):
            outputs.append(Output(name=named_output, example=False))

        # handle example outputs
        example_outputs = kwds.pop("example_output", [])
        for i, output_file in enumerate(example_outputs or []):
            name = "output%d" % (i + 1)
            from_path = output_file
            use_from_path = True
            if output_file in cheetah_template:
                # Actually found the file in the command, assume it can
                # be specified directly and skip from_work_dir.
                use_from_path = False
            output = Output(name=name, from_path=from_path,
                            use_from_path=use_from_path, example=True)
            outputs.append(output)
            cheetah_template = _replace_file_in_command(cheetah_template, output_file, output.name)

        self.inputs = inputs
        self.outputs = outputs
        self.command = command
        self.cheetah_template = cheetah_template

    def example_input_names(self):
        for input in self.inputs:
            if input.example:
                yield input.input_description

    def example_output_names(self):
        for output in self.outputs:
            if output.example:
                yield output.example_path

    def cwl_lex_list(self):
        if not self.command:
            return []

        command_parts = shlex.split(self.command)
        parse_list = []

        input_count = 0
        output_count = 0

        index = 0

        prefixed_parts = []
        while index < len(command_parts):
            value = command_parts[index]
            eq_split = value.split("=")

            prefix = None
            if not _looks_like_start_of_prefix(index, command_parts):
                index += 1
            elif len(eq_split) == 2:
                prefix = Prefix(eq_split[0] + "=", False)
                value = eq_split[1]
                index += 1
            else:
                prefix = Prefix(value, True)
                value = command_parts[index + 1]
                index += 2
            prefixed_parts.append((prefix, value))

        for position, (prefix, value) in enumerate(prefixed_parts):
            if value in self.example_input_names():
                input_count += 1
                input = _CwlInput(
                    "input%d" % input_count,
                    position,
                    prefix,
                    value,
                )
                parse_list.append(input)
            elif value in self.example_output_names():
                output_count += 1
                output = _CwlOutput(
                    "output%d" % output_count,
                    position,
                    prefix,
                    value,
                )
                parse_list.append(output)
            elif prefix:
                param_id = prefix.prefix.lower().rstrip("=")
                type_ = param_type(value)
                input = _CwlInput(
                    param_id,
                    position,
                    prefix,
                    value,
                    type_=type_,
                )
                parse_list.append(input)
            else:
                part = _CwlCommandPart(value, position, prefix)
                parse_list.append(part)
        return parse_list

    def cwl_properties(self):
        base_command = []
        arguments = []
        inputs = []
        outputs = []

        lex_list = self.cwl_lex_list()

        index = 0
        while index < len(lex_list):
            token = lex_list[index]
            if isinstance(token, _CwlCommandPart):
                base_command.append(token.value)
            else:
                break
            index += 1

        while index < len(lex_list):
            token = lex_list[index]
            if token.is_token(">"):
                break
            token.position = index - len(base_command) + 1
            if isinstance(token, _CwlCommandPart):
                arguments.append(token)
            elif isinstance(token, _CwlInput):
                inputs.append(token)
            elif isinstance(token, _CwlOutput):
                token.glob = "$(inputs.%s)" % token.id
                outputs.append(token)

            index += 1

        stdout = None
        if index < len(lex_list):
            token = lex_list[index]
            if token.is_token(">") and (index + 1) < len(lex_list):
                output_token = lex_list[index + 1]
                if not isinstance(output_token, _CwlOutput):
                    output_token = _CwlOutput("std_out", None)

                output_token.glob = "out"
                output_token.require_filename = False
                outputs.append(output_token)
                stdout = "out"
                index += 2
            else:
                io.warn("Example command too complex, you will need to build it up manually.")

        return {
            "inputs": inputs,
            "outputs": outputs,
            "arguments": arguments,
            "base_command": base_command,
            "stdout": stdout,
        }

    def test_case(self):
        test_case = TestCase()
        for input in self.inputs:
            if input.example:
                test_case.params.append((input.name, input.input_description))

        for output in self.outputs:
            if output.example:
                test_case.outputs.append((output.name, output.example_path))

        return test_case


def _looks_like_start_of_prefix(index, parts):
    value = parts[index]
    if len(value.split("=")) == 2:
        return True
    if index + 1 == len(parts):
        return False
    next_value = parts[index + 1]
    next_value_is_not_start = (len(value.split("=")) != 2) and next_value[0] not in ["-", ">", "<", "|"]
    return value.startswith("-") and next_value_is_not_start


Prefix = namedtuple("Prefix", ["prefix", "separated"])


class _CwlCommandPart(object):

    def __init__(self, value, position, prefix):
        self.value = value
        self.position = position
        self.prefix = prefix

    def is_token(self, value):
        return self.value == value


class _CwlInput(object):

    def __init__(self, id, position, prefix, example_value, type_="File"):
        self.id = id
        self.position = position
        self.prefix = prefix
        self.example_value = example_value
        self.type = type_

    def is_token(self, value):
        return False


class _CwlOutput(object):

    def __init__(self, id, position, prefix, example_value):
        self.id = id
        self.position = position
        self.prefix = prefix
        self.glob = None
        self.example_value = example_value
        self.require_filename = True

    def is_token(self, value):
        return False


def _render(kwds, template_str=TOOL_TEMPLATE):
    """Render template variables to generate the final tool."""
    return templates.render(template_str, **kwds)


def _replace_file_in_command(command, specified_file, name):
    """Replace example file with cheetah variable name.

    Be sure to single quote the name.
    """
    # TODO: check if the supplied variant was single quoted already.
    if '"%s"' % specified_file in command:
        # Sample command already wrapped filename in double quotes
        command = command.replace('"%s"' % specified_file, "'$%s'" % name)
    elif (" %s " % specified_file) in (" " + command + " "):
        # In case of spaces, best to wrap filename in double quotes
        command = command.replace(specified_file, "'$%s'" % name)
    else:
        command = command.replace(specified_file, '$%s' % name)
    return command


def _handle_help(kwds):
    """Convert supplied help parameters into a help variable for template.

    If help_text is supplied, use as is. If help is specified from a command,
    run the command and use that help text.
    """
    help_text = kwds.get("help_text")
    if not help_text:
        help_from_command = kwds.get("help_from_command")
        if help_from_command:
            p = subprocess.Popen(
                help_from_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            help_text = p.communicate()[0]

    del kwds["help_text"]
    del kwds["help_from_command"]

    kwds["help"] = help_text


def _handle_tests(kwds, test_case):
    """Build tool test abstractions.

    Given state built up from handling rest of arguments (test_case) and
    supplied kwds - build tests for template and corresponding test files.
    """
    test_files = []
    if kwds["test_case"]:
        tests = [test_case]
        test_files.extend(map(lambda x: x[1], test_case.params))
        test_files.extend(map(lambda x: x[1], test_case.outputs))
    else:
        tests = []
    return tests, test_files


def _handle_requirements(kwds):
    """Build tool requirement abstractions.

    Convert requirements and containers specified from the command-line
    into abstract format for consumption by the template.
    """
    requirements = kwds["requirement"]
    del kwds["requirement"]
    requirements = list(map(Requirement, requirements or []))

    container = kwds["container"]
    del kwds["container"]
    containers = list(map(Container, container or []))

    kwds["requirements"] = requirements
    kwds["containers"] = containers


def _find_command(kwds):
    """Find base command from supplied arguments or just return `None`.

    If no such command was supplied (template will just replace this
    with a TODO item).
    """
    command = kwds.get("command")
    if not command:
        command = kwds.get("example_command", None)
        if command:
            del kwds["example_command"]
    return command


class UrlCitation(object):
    """Describe citation for tool."""

    def __init__(self, url):
        self.url = url

    def __str__(self):
        if "github.com" in self.url:
            return self._github_str()
        else:
            return self._url_str()

    def _github_str(self):
        url = self.url
        title = url.split("/")[-1]
        return '''
@misc{github%s,
  author = {LastTODO, FirstTODO},
  year = {TODO},
  title = {%s},
  publisher = {GitHub},
  journal = {GitHub repository},
  url = {%s},
}''' % (title, title, url)

    def _url_str(self):
        url = self.url
        return '''
@misc{renameTODO,
  author = {LastTODO, FirstTODO},
  year = {TODO},
  title = {TODO},
  url = {%s},
}''' % (url)


class ToolDescription(object):
    """An description of the tool and related files to create."""

    def __init__(self, contents, tool_files=None, test_files=[]):
        self.contents = contents
        self.tool_files = tool_files or []
        self.test_files = test_files


class ToolFile(object):

    def __init__(self, filename, contents, description):
        self.filename = filename
        self.contents = contents
        self.description = description


class Input(object):

    def __init__(self, input_description, name=None, example=False):
        parts = input_description.split(".")
        name = name or parts[0]
        if len(parts) > 0:
            datatype = ".".join(parts[1:])
        else:
            datatype = "data"

        self.input_description = input_description
        self.example = example
        self.name = name
        self.datatype = datatype

    def __str__(self):
        template = '<param type="data" name="{0}" format="{1}" />'
        self.datatype = self.datatype.split(".")[-1]
        return template.format(self.name, self.datatype)


class Output(object):

    def __init__(self, from_path=None, name=None, use_from_path=False, example=False):
        if from_path:
            parts = from_path.split(".")
            name = name or parts[0]
            if len(parts) > 1:
                datatype = ".".join(parts[1:])
            else:
                datatype = "data"
        else:
            name = name
            datatype = "data"

        self.name = name
        self.datatype = datatype
        if use_from_path:
            self.from_path = from_path
        else:
            self.from_path = None
        self.example = example
        if example:
            self.example_path = from_path

    def __str__(self):
        if self.from_path:
            return self._from_path_str()
        else:
            return self._named_str()

    def _from_path_str(self):
        template = '<data name="{0}" format="{1}" from_work_dir="{2}" />'
        return template.format(self.name, self.datatype, self.from_path)

    def _named_str(self):
        template = '<data name="{0}" format="{1}" />'
        return template.format(self.name, self.datatype)


class Requirement(object):

    def __init__(self, requirement):
        parts = requirement.split("@", 1)
        if len(parts) > 1:
            name = parts[0]
            version = "@".join(parts[1:])
        else:
            name = parts[0]
            version = None
        self.name = name
        self.version = version

    def __str__(self):
        base = '<requirement type="package"{0}>{1}</requirement>'
        if self.version is not None:
            attrs = ' version="{0}"'.format(self.version)
        else:
            attrs = ''
        return base.format(attrs, self.name)


def param_type(value):
    if re.match(r"^\d+$", value):
        return "int"
    elif re.match(r"^\d+?\.\d+?$", value):
        return "float"
    else:
        return "string"


class Container(object):

    def __init__(self, image_id):
        self.type = "docker"
        self.image_id = image_id

    def __str__(self):
        template = '<container type="{0}">{1}</container>'
        return template.format(self.type, self.image_id)


class TestCase(object):

    def __init__(self):
        self.params = []
        self.outputs = []


def write_tool_description(ctx, tool_description, **kwds):
    """Write a tool description to the file system guided by supplied CLI kwds."""
    tool_id = kwds.get("id")
    output = kwds.get("tool")
    if not output:
        extension = "cwl" if kwds.get("cwl") else "xml"
        output = "%s.%s" % (tool_id, extension)
    if not io.can_write_to_path(output, **kwds):
        ctx.exit(1)

    io.write_file(output, tool_description.contents)
    io.info("Tool written to %s" % output)
    for tool_file in tool_description.tool_files:
        if tool_file.contents is None:
            continue

        path = tool_file.filename
        if not io.can_write_to_path(path, **kwds):
            ctx.exit(1)
        io.write_file(path, tool_file.contents)
        io.info("Tool %s written to %s" % (tool_file.description, path))

    macros = kwds["macros"]
    macros_file = "macros.xml"
    if macros and not os.path.exists(macros_file):
        io.write_file(macros_file, tool_description.macro_contents)
    elif macros:
        io.info(REUSING_MACROS_MESSAGE)
    if tool_description.test_files:
        if not os.path.exists("test-data"):
            io.info("No test-data directory, creating one.")
            os.makedirs('test-data')
        for test_file in tool_description.test_files:
            io.info("Copying test-file %s" % test_file)
            try:
                shutil.copy(test_file, 'test-data')
            except Exception as e:
                io.info("Copy of %s failed: %s" % (test_file, e))


__all__ = (
    "build",
    "ToolDescription",
    "write_tool_description",
)
