SIMPLE_TYPES_GALAXY = ["data", "data_collection", "boolean", "integer", "float", "field", "text"]
def get_command(i):
    # we are supposing for now that we can't do arrays of arrays of arrays. 
    # # TODO : records of arrays .
    command = ""
    if i.optional:
        command += "#if $" + str(i.name) +":\n"
    if i.type == "repeat":
        command += "echo \'"
        command += str(i.name) + ":"
        command += "\' >> $job_gal ;\n"
        if i.array_input.type == "data_collection":
            command += "#for $i, $s in enumerate($" + str(i.name) +"): \n"
            command += "mkdir " + i.array_input.name +"_$i ; \n"
            command += "#for $j, $t in enumerate($s." + str(i.array_input.name) +"): \n"
            command += "ln -s $t ./" + i.array_input.name + "_$i/$t.element_identifier ; \n"
            command += "#end for \n"
            command += "cd " + i.array_input.name + "_$i ; \n"
            command += "echo \'   - {class: Directory, path: \' >> $job_gal ; \n"
            command += "echo \$PWD >> $job_gal ;\n"
            command += "echo \'}\' >> $job_gal ;\n"
            command += "cd .. ; \n"
            
        elif i.array_input.type in SIMPLE_TYPES_GALAXY :
            command += "#for $i, $s in enumerate($" + str(i.name) +"): \n"
            command += "echo \'"
            command += "  - " + input_to_yaml(i.array_input, prefix = "$s", array = "True", record = False) # Can be array of records
            command += "\' >> $job_gal ;\n"

        else:
            command += "#for $i, $s in enumerate($" + str(i.name) +"): \n"
            command += "echo \'  - \' >> $job_gal ;\n"

            if i.array_input.type == "repeat":
                if i.array_input.array_input.type in SIMPLE_TYPES_GALAXY :
                    command += "#for $j, $t in enumerate($s." + str(i.array_input.name) +"): \n"
                    command += "echo \'"
                    command += "    - " + input_to_yaml(i.array_input.array_input, prefix ="$t." + i.array_input.array_input.name, array = True, record = False) # Can be array of records
                    command += "\' >> $job_gal ;\n"
                    command += "#end for \n"

            elif i.array_input.type == "section":
                for input in i.array_input.record_inputs:
                    if not input.type == "array" and not input.type == "record" :
                        command += "echo \'       " + input_to_yaml(input, prefix="$s." + i.array_input.name, array =False, record= True)
                        command += "\' >> $job_gal ;\n"
        command += "#end for \n"

    elif i.multiple and i.type == "data":
        command += "echo \'"
        command += str(i.name) + ":"
        command += "\' >> $job_gal ;\n"
        command += "#for $i, $s in enumerate($" + str(i.name) +"): \n"
        command += "echo \'"
        command += "  - " + input_to_yaml(i, prefix= "$s", array = True, record = False) # Can be array of records
        command += "\' >> $job_gal ;\n"
        command += "#end for \n"

    elif i.type == "section" :
        command += "echo \'"
        command += str(i.name) + ":"
        command += "\' >> $job_gal ;\n"
        for input in i.record_inputs:
            input.source = i.name
            if not input.type == "array" and not input.type == "record" :
                command += "echo \'"
                command += "  " + input_to_yaml(input, prefix="", array =False, record= True)
                command += "\' >> $job_gal ;\n"

    elif i.type == "text" or i.type == "integer" or i.type == "float" or i.type == "boolean" or i.type == "select" or i.type == "data":
        command += "echo \'"
        command += input_to_yaml(i, "", False, False)
        command += "\' >> $job_gal ;\n"

    elif i.type == "data_collection":
        command += "mkdir " + i.name +"; \n"
        command += "#for $i, $s in enumerate($" + str(i.name) +"): \n"
        command += "ln -s $s ./" + i.name + "/$s.element_identifier ; \n"
        command += "#end for \n"
        command += "cd " + i.name + "; \n"
        command += "echo \'" + i.name + ": {class: Directory, path: \' >> $job_gal ; \n"
        command += "echo \$PWD >> $job_gal ;\n"
        command += "echo \'}\' >> $job_gal ;\n"

    else:
        print("no input") #raise exception
    if i.optional:
        command += "#end if\n"
    return command

def input_to_yaml(i, prefix, array, record):
    """ Transcribe inputs for the yaml file """

    yaml = ""
    if record :
        if i.type == "text" or i.type == "integer" or i.type == "float" or i.type == "boolean" or i.type == "select":     
            yaml += str(i.name) + ": " + prefix + "." + str(i.name)
            
        elif i.type == "data":
            yaml +=str(i.name) +": " + "{class: File, path: " + prefix +"."+str(i.name)
            if i.format:
                yaml += ", format: " + str(i.format)
            yaml += "}"

 
    elif array :
        if i.type == "data" :
            if i.multiple:
                yaml += "{class: File, path: " + prefix
                if i.format :
                    yaml += " format: " + str(i.format)
                yaml += " }"
            else:
                yaml += "{class: File, path: " + prefix +'.'+ str(i.name)
                if i.format :
                    yaml += " format: " + str(i.format)
                yaml += " }"

        if i.type == "text" or i.type == "integer" or i.type == "float" or i.type == "boolean" or i.type == "select":
            yaml += prefix + '.'+ str(i.name)

    
    elif i.type == "text" or i.type == "integer" or i.type == "float" or i.type == "boolean" or i.type == "select":     
        yaml += str(i.name)+": $"+str(i.name)
        
    elif i.type == "data":
        yaml +=str(i.name) +": " + "{class: File, path: $" + str(i.name)
        if i.format:
            yaml += ", format: " + str(i.format)
        yaml += "}"

    elif i.type == "data_collection":
        yaml +=str(i.name) +": " + "{class: Directory, path: ./" + str(i.name) + " }"
    else:
        print("no input") #raise exception

    return yaml