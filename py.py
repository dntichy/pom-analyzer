import os
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import ParseError

def find_pom_files(directory, include_subfolders=False):
    pom_files = []
    if include_subfolders:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file == 'pom.xml':
                    pom_files.append(os.path.join(root, file))
    else:
        subfolders = [f.path for f in os.scandir(directory) if f.is_dir()]
        for subfolder in subfolders:
            pom_file = os.path.join(subfolder, 'pom.xml')
            if os.path.exists(pom_file):
                pom_files.append(pom_file)
    return pom_files

def resolve_property(pom_tree, prop_name):
    namespaces = {'ns': 'http://maven.apache.org/POM/4.0.0'}
    properties = pom_tree.find('ns:properties', namespaces)
    if properties is not None:
        prop_element = properties.find(f'ns:{prop_name}', namespaces)
        if prop_element is not None:
            return prop_element.text
    return None

def read_env_variables(project_path):
    env_variables = {}
    properties_path = os.path.join(project_path, 'src', 'main', 'resources', 'application.properties')
    if os.path.exists(properties_path):
        with open(properties_path, 'r') as prop_file:
            for line in prop_file:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        key, value = line.split('=', 1)
                        env_variables[key.strip()] = value.strip()
                    except ValueError:
                        pass  # Ignore lines that cannot be split using '='
    return env_variables


def extract_project_info(pom_file):
    try:
        tree = ET.parse(pom_file)
        root = tree.getroot()
        namespaces = {'ns': 'http://maven.apache.org/POM/4.0.0'}
        group_id_element = root.find('ns:groupId', namespaces)
        artifact_id_element = root.find('ns:artifactId', namespaces)
        if group_id_element is not None and artifact_id_element is not None:
            group_id = group_id_element.text
            artifact_id = artifact_id_element.text
            project_name = f"{group_id}:<b>{artifact_id}</b>"
            api_dependencies = []
            dependencies = []
            for artifactItem in root.findall('.//ns:artifactItem', namespaces):
                api_group_id = artifactItem.find('ns:groupId', namespaces).text
                api_artifact_id = artifactItem.find('ns:artifactId', namespaces).text
                version_element = artifactItem.find('ns:version', namespaces)
                if version_element is not None:
                    version_text = version_element.text
                    if "${" in version_text and "}" in version_text:
                        prop_name = version_text[2:-1]  # Extract property name
                        resolved_version = resolve_property(root, prop_name)
                        if resolved_version:
                            api_dependencies.append(f"{api_group_id}:{api_artifact_id} ({resolved_version})")
                        else:
                            api_dependencies.append(f"{api_group_id}:{api_artifact_id} ({version_text})")
                    else:
                        api_dependencies.append(f"{api_group_id}:{api_artifact_id} ({version_text})")
                else:
                    api_dependencies.append(f"{api_group_id}:{api_artifact_id}")
            for dependency in root.findall('.//ns:dependency', namespaces):
                dep_group_id = dependency.find('ns:groupId', namespaces).text
                dep_artifact_id = dependency.find('ns:artifactId', namespaces).text
                dependencies.append(f"{dep_group_id}:{dep_artifact_id}")
            project_path = os.path.dirname(pom_file)
            env_variables = read_env_variables(project_path)
            return project_name, sorted(api_dependencies), dependencies, env_variables, pom_file
        else:
            print(f"Missing groupId or artifactId in {pom_file}. Skipping this file.")
            return None, None, None, None, None
    except (ParseError, AttributeError):
        print(f"Error parsing {pom_file}. Skipping this file.")
        return None, None, None, None, None

def process_projects(directory, output_file, include_subfolders=True):
    pom_files = find_pom_files(directory, include_subfolders)
    html_content = "<style>"
    html_content += "table { width: 100%; border-collapse: collapse; }"
    html_content += "th, td { border: 1px solid black; padding: 8px; text-align: left; }"
    html_content += "th { background-color: #f2f2f2; }"
    html_content += ".path-column { width: 150px; word-wrap: break-word; }"
    html_content += "</style>"
    html_content += "<div style='overflow-x:auto;'>"
    html_content += "<table>"
    html_content += "<tr><th>#</th><th>Project Name</th><th style='width: 200px;'>Path to pom.xml</th><th>API Dependencies</th><th>Dependencies</th><th>ENV Variables</th></tr>"
    
    project_counter = 1
    for pom_file in pom_files:
        project_name, api_dependencies, dependencies, env_variables, pom_file_path = extract_project_info(pom_file)
        if project_name is not None:
            html_content += "<tr>"
            html_content += f"<td>{project_counter}</td>"
            html_content += f"<td>{project_name}</td>"
            html_content += f"<td class='path-column'>{pom_file_path}</td>"
            html_content += "<td>"
            if api_dependencies:
                html_content += "<ul>"
                for api_dep in api_dependencies:
                    html_content += f"<li>{api_dep}</li>"
                html_content += "</ul>"
            html_content += "</td>"
            html_content += "<td>"
            if dependencies:
                html_content += "<ul>"
                for dep in dependencies:
                    html_content += f"<li>{dep}</li>"
                html_content += "</ul>"
            html_content += "</td>"
            html_content += "<td>"
            if env_variables:
                html_content += "<ul>"
                for key, value in env_variables.items():
                    html_content += f"<li>{key}: {value}</li>"
                html_content += "</ul>"
            html_content += "</td>"
            html_content += "</tr>"
            project_counter += 1
    
    html_content += "</table>"
    html_content += "</div>"
    with open(output_file, 'w') as f:
        f.write(html_content)

if __name__ == "__main__":
    default_directory = r"D:\projects\adr"
    directory = input(f"Enter the directory to search for projects (default: {default_directory}): ") or default_directory
    include_subfolders = input("Analyze subfolders as well? (y/n, default: n): ").lower() == 'y'
    output_file = input("Enter the output HTML file name (default: dependency_report.html): ") or "dependency_report.html"
    process_projects(directory, output_file, include_subfolders)
