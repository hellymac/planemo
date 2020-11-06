#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool

inputs:
  - id: syntaxB
    type:
      type: array
      items:
        type: array
        items: string
  - id: inp
    type:
      type: array
      items:
        type: record
        name: instr
        fields:
          - name: instr
            type: string
  - id: libraries_metadata
    type:
      type: array
      items:
        type: record
        name: rec
        fields:
          - name: lib_index
            type: int?
          - name: orientation
            type: string?
          - name: lib_type
            type: string?
outputs: []
baseCommand: echo
