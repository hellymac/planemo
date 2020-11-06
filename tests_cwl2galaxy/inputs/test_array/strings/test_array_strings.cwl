#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
inputs:
  syntaxA:
    type: string[]
    inputBinding:
      prefix: -A
      position: 1

  syntaxB:
    type:
      type: array
      items: string
      inputBinding:
        prefix: -B=
        separate: false
    inputBinding:
      position: 2

  syntaxC:
    type:
      - 'null'
      - type: array
        items: string
    inputBinding:
      prefix: -C=
      itemSeparator: ","
      separate: false
      position: 4
outputs: []
baseCommand: echo
