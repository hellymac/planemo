cwlVersion: v1.0
class: CommandLineTool

baseCommand: echo
inputs:
  header:
    type:
      - 'null'
      - type: enum
        symbols:
          - include
          - exclude
          - only
    default: include
    inputBinding:
      position: 1
outputs: []
