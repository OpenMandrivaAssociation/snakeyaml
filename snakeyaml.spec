Name:		snakeyaml
Version:	2.7
Release:	1
Summary:	YAML 1.1 parser and emitter for Java
Group:		Development/Java
License:	ASL 2.0
URL:		https://codeberg.org/snakeyaml/snakeyaml
Source0:	https://codeberg.org/snakeyaml/snakeyaml/archive/snakeyaml-%{version}.tar.gz#/snakeyaml-%{version}.tar.gz

BuildArch:	noarch
Obsoletes:	%{name}-javadoc < 2
# Literal, so the first rpmbuild -bs records them before sysjar is installed.
BuildRequires:	maven
BuildRequires:	java-current-devel
BuildSystem:	maven

%description
SnakeYAML reads and writes YAML 1.1. 2.0 stops constructing arbitrary
Java classes from untrusted input unless the caller names them.
2.7 is the current release and builds on Java 8. Tests are skipped.
The multi-release module-info is not attached.

%prep
%setup -q -n snakeyaml
# Bundle packaging and central-publishing are build extensions we do not
# package. The Java 9 execution asks for a toolchain definition.
python - <<'PY'
import xml.etree.ElementTree as ET
from pathlib import Path

ET.register_namespace("", "http://maven.apache.org/POM/4.0.0")
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")
drop_plugins = {"maven-bundle-plugin", "central-publishing-maven-plugin"}

def local(tag):
    return tag.rsplit("}", 1)[-1]

path = Path("pom.xml")
tree = ET.parse(path)
root = tree.getroot()
packaging = None
removed = []
executions = 0
for parent in root.iter():
    for child in list(parent):
        if local(child.tag) == "packaging" and (child.text or "").strip() == "bundle":
            child.text = "jar"
            packaging = "jar"
        if local(child.tag) == "execution":
            ident = ""
            for item in child:
                if local(item.tag) == "id":
                    ident = (item.text or "").strip()
            if ident == "module-info-compile":
                parent.remove(child)
                executions += 1
            continue
        if local(child.tag) != "plugin":
            continue
        artifact = ""
        for item in child:
            if local(item.tag) == "artifactId":
                artifact = (item.text or "").strip()
        if artifact in drop_plugins:
            parent.remove(child)
            removed.append(artifact)
missing = sorted(drop_plugins - set(removed))
if packaging != "jar" or missing or executions != 1:
    raise SystemExit(f"packaging={packaging} missing={missing} executions={executions}")
tree.write(path, encoding="UTF-8", xml_declaration=True)
PY

%files -f .mfiles
%doc LICENSE.txt README.md
