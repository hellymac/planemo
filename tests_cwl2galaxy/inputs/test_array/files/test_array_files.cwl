#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
inputs:
  syntaxA:
    type: File[]?
    inputBinding:
      prefix: -A
      position: 1

  syntaxB:
    type:
      type: array
      items: File
      inputBinding:
        prefix: -B=
        separate: false
    inputBinding:
      position: 2

  syntaxC:
    type:
      - 'null'
      - type: array
        items: File
    inputBinding:
      prefix: -C=
      itemSeparator: ","
      separate: false
      position: 4
outputs: []
baseCommand: echo
