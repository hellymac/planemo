#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
inputs:
  dependent_parameters:
    type:
      type: record
      name: dependent_parameters
      fields:
        itemA:
          type: string
          inputBinding:
            prefix: -A
        itemB:
          type: string
          inputBinding:
            prefix: -B
  # exclusive_parameters:
  #   type:
  #     - type: record
  #       name: itemC
  #       fields:
  #         itemC:
  #           type: string
outputs: []
baseCommand: echo
