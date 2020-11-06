cwlVersion: v1.0
class: CommandLineTool
id: edam
baseCommand: echo "test"
inputs:
  bam:
    format: edam:format_2572
    type: File
outputs: []
$namespaces:
  edam: http://edamontology.org/
$schemas:
  - http://edamontology.org/EDAM_1.18.owl
