# J AI Platform 1.0

J OS is the runtime. J Agent runs on top of J OS. Applications connect to J OS and are managed/orchestrated by J Agent.

J AI Cloud is the managed deployment of J OS. The same runtime contract can be deployed locally/self-hosted.

```text
J AI Cloud
    |
   J OS  (runtime)
    |
  J Agent
    |
    +-- J Mobile
    +-- J Desktop
    +-- J CLI
    |
    +-- J Verify
    +-- J Tester
    +-- J Security
    +-- J Alert
    +-- J Care
```

The Symfony website is only the public website and members/control area. It provisions and manages customer agents through the J OS cloud control API; it is not the runtime.

## Deployment modes

Cloud:
`Symfony Members Area -> J AI Cloud -> J OS -> J Agent -> applications`

Local:
`J Mobile/Desktop/CLI -> local J OS -> J Agent -> applications`

Both use the same J OS application contract so applications remain deployment-neutral.
