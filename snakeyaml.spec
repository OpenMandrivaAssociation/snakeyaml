Name:		snakeyaml
Version:	2.7
Release:	3
Summary:	YAML 1.1 parser and emitter for Java
Group:		Development/Java
License:	ASL 2.0
URL:		https://codeberg.org/snakeyaml/snakeyaml
Source0:	https://codeberg.org/snakeyaml/snakeyaml/archive/snakeyaml-%{version}.tar.gz#/snakeyaml-%{version}.tar.gz
# Gradle 9.9.1 strictly pins 2.6. 2.7 stays the default jar.
Source1:	https://codeberg.org/snakeyaml/snakeyaml/archive/snakeyaml-2.6.tar.gz#/snakeyaml-2.6.tar.gz

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
The jar's automatic module name is org.yaml.snakeyaml. The upstream
module-info compile stays out because it asks for a Java toolchain.
Gradle 9.9.1 strictly pins 2.6, so that jar is installed beside 2.7.

%prep
%setup -q -n snakeyaml
%setup -q -T -D -a 1 -n snakeyaml
find snakeyaml-2.6 -name '*.jar' -delete
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

%build -a
printf 'Automatic-Module-Name: org.yaml.snakeyaml\n' > target/auto-module.mf
jar ufm target/snakeyaml-%{version}.jar target/auto-module.mf
java --module-path target/snakeyaml-%{version}.jar --describe-module org.yaml.snakeyaml | grep -q '^org.yaml.snakeyaml'
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java}"
mkdir -p snakeyaml26/classes
find snakeyaml-2.6/src/main/java -name '*.java' > snakeyaml26/sources.list
test -s snakeyaml26/sources.list
"$JAVA_HOME/bin/javac" --release 8 -encoding UTF-8 -Xlint:-options \
	-d snakeyaml26/classes @snakeyaml26/sources.list
"$JAVA_HOME/bin/jar" cf snakeyaml26/snakeyaml.jar -C snakeyaml26/classes .
cat > snakeyaml26/snakeyaml.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.yaml</groupId>
  <artifactId>snakeyaml</artifactId>
  <version>2.6</version>
  <name>SnakeYAML</name>
  <description>YAML 1.1 parser and emitter for Java.</description>
  <url>https://codeberg.org/snakeyaml/snakeyaml</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
</project>
EOF

%install -p
sysjar install --buildroot %{buildroot} \
	--artifact snakeyaml26/snakeyaml.pom:snakeyaml26/snakeyaml.jar \
	--file-name snakeyaml-2.6 \
	--filelist .mfiles26
# 2.7 owns snakeyaml.sysjar. 2.6 keeps a second index file.
/bin/mv %{buildroot}/usr/share/sysjar/index/org.yaml/snakeyaml.sysjar \
	%{buildroot}/usr/share/sysjar/index/org.yaml/snakeyaml-2.6.sysjar
sed -i 's|/usr/share/sysjar/index/org.yaml/snakeyaml\.sysjar|/usr/share/sysjar/index/org.yaml/snakeyaml-2.6.sysjar|' .mfiles26

%install -a
while IFS= read -r line; do
	grep -qxF -- "$line" .mfiles || printf '%s\n' "$line" >> .mfiles
done < .mfiles26

%check -a
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java}"
cat > YamlSmoke.java << 'EOF'
import org.yaml.snakeyaml.Yaml;
public class YamlSmoke {
	public static void main(String[] args) {
		Object loaded = new Yaml().load("answer: 42");
		Object value = ((java.util.Map) loaded).get("answer");
		if (!Integer.valueOf(42).equals(value)) {
			throw new AssertionError(value);
		}
		System.out.println(args[0] + " " + value);
	}
}
EOF
"$JAVA_HOME/bin/javac" --release 8 -encoding UTF-8 -Xlint:-options \
	-cp %{buildroot}%{_javadir}/snakeyaml.jar YamlSmoke.java
"$JAVA_HOME/bin/java" -cp "%{buildroot}%{_javadir}/snakeyaml.jar:." YamlSmoke snakeyaml27_ok | tee check27.log
grep -F -q 'snakeyaml27_ok 42' check27.log
"$JAVA_HOME/bin/javac" --release 8 -encoding UTF-8 -Xlint:-options \
	-cp %{buildroot}%{_javadir}/snakeyaml-2.6.jar YamlSmoke.java
"$JAVA_HOME/bin/java" -cp "%{buildroot}%{_javadir}/snakeyaml-2.6.jar:." YamlSmoke snakeyaml26_ok | tee check26.log
grep -F -q 'snakeyaml26_ok 42' check26.log

%files -f .mfiles
%doc LICENSE.txt README.md
