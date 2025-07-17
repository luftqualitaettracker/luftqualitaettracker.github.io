import platform
import os

hardware_info = f"""\
"""

html_content = f"""
<html>
<head>
    <title>Hardware Info</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
<div class="terminal">
    <div class="prompt"><span class="user">pi@raspberrypi</span>:<span class="dir">~</span>$ <span class="cmd">neofetch</span></div>
    <pre class="output">
   .~~.   .~~.     Hardware Info
  '. \ ' ' / .'    ----------------
   .~ .~~~..~.
  : .~.'~'.~. :    System:     {platform.system()}
 ~ (   ) (   ) ~   Machine:    {platform.machine()}
( : '~'.~.'~' : )  Processor:  {platform.processor()}
 ~ .~ (   ) ~. ~   CPU count:  {os.cpu_count()}
  (  : '~' :  )
   '~ .~~~. ~'
       '~'
    </pre>
</div>
</body>
</html>
"""

with open("/usr/share/nginx/html/index.html", "w") as f:
    f.write(html_content)
