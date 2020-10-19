
def get_command(i):

    command = ""
    if i.array :
        command += "echo \'"
        command += str(i.name) + ":"
        command += "\' >> $job_gal ;\n"
        command += "#for $i, $s in enumerate($" + str(i.name) +"): \n"
        if i.type == "text" or i.type == "integer" or i.type == "float" or i.type == "boolean" or i.type == "select" or i.type == "data":
            command += "echo \'"
            command += "  - " + input_to_yaml(i, array = i.array, record = False) # Can be array of records
            command += "\' >> $job_gal ;\n"
        if i.record :
            print("array of records") # TODO
        command += "#end for \n"

    elif i.record :
        command += "echo \'"
        command += str(i.name) + ":"
        command += "\' >> $job_gal ;\n"
        for input in i.record_inputs:
            input.source = i.name
            if not input.array and not input.record :
                command += "echo \'"
                command += "  " + input_to_yaml(input, array =False, record= True)
                command += "\' >> $job_gal ;\n"

    elif i.type == "text" or i.type == "integer" or i.type == "float" or i.type == "boolean" or i.type == "select" or i.type == "data":
        command += "echo \'"
        command += input_to_yaml(i, False, False)
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

    return command

def input_to_yaml(i, array, record):
    """ Transcribe inputs for the yaml file """

    yaml = ""
    if record :
        if i.type == "text" or i.type == "integer" or i.type == "float" or i.type == "boolean" or i.type == "select":     
            yaml += str(i.name)+": $"+str(i.source)+"."+str(i.name)
            
        elif i.type == "data":
            yaml +=str(i.name) +": " + "{class: File, path: $" + str(i.source)+"."+str(i.name)
            if i.format:
                yaml += ", format: " + str(i.format)
            yaml += "}"

 
    elif array :
        if i.type == "data" :
            yaml += "{class: File, path: $s"
            if i.format :
                 yaml += " format: " + str(i.format)
            yaml += " }"

        if i.type == "text" or i.type == "integer" or i.type == "float" or i.type == "boolean" or i.type == "select":
            yaml += "$s."+str(i.name)

    
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