cwlVersion: v1.0
class: CommandLineTool

requirements:
  InlineJavascriptRequirement: {}
hints:
  ResourceRequirement:
    coresMin: 1
    ramMin: 10000
  DockerRequirement:
    dockerPull: kerstenbreuer/samtools:1.7

baseCommand: [samtools, view]
inputs:
  bam:
    format: edam:format_2572
    doc: aligned reads to be checked in bam format
    type: File
    inputBinding:
      position: 10

  count:
    type: boolean?
    default: true
    doc: "Instead of printing the alignments, only count them and print the total number."
    inputBinding:
      position: 1
      prefix: -c
  exclude_unmapped:
    type: boolean?
    default: true
    inputBinding:
      valueFrom: "4"
      prefix: -F
      position: 1

  is_paired_end:
    doc: if paired end, only properly paired reads pass
    type: boolean
    default: true

  min_mapping_quality:
    doc: Reads with a mapping quality below this will be excluded
    type: int?
    default: 20
    inputBinding:
      position: 1
      prefix: -q


  header:
    type:
      - 'null'
      - type: enum
        symbols:
          - include
          - exclude
          - only
    default: include
outputs: 
  test:
    type: stdout
stdout: test.txt

$namespaces:
  edam: http://edamontology.org/
$schemas:
  - http://edamontology.org/EDAM_1.18.owl
