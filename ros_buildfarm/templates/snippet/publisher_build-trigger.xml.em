    <hudson.tasks.BuildTrigger>
      <childProjects>@ESCAPE(','.join(sorted(child_projects)))</childProjects>
      <threshold>
        <name>UNSTABLE</name>
        <ordinal>1</ordinal>
        <color>YELLOW</color>
        <completeBuild>true</completeBuild>
      </threshold>
    </hudson.tasks.BuildTrigger>