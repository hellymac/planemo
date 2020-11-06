class: CommandLineTool
cwlVersion: v1.0
baseCommand: ls

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: example.txt
        entry: |-
          PREFIX='Message is:'
          MSG="\${PREFIX} $(inputs.message)"
          echo \${MSG}
      - entryname: example2.txt
        entry: "hello 2"
      - entryname: example3.txt
        entry: "hello 3"
      - entryname: example.sh
        entry: "shoud not be returned"


inputs:
  message: string
outputs:
  example_array_out:
    type: File[]
    outputBinding:
      glob: example*.txt
