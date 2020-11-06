class: CommandLineTool
cwlVersion: v1.0
baseCommand: ["cat", "example.txt"]

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: example.txt
        entry: |-
          PREFIX='Message is:'
          MSG="\${PREFIX} $(inputs.message)"
          echo \${MSG}

inputs:
  message: string
outputs:
  example_out:
    type: File
    outputBinding:
      glob: example.txt
