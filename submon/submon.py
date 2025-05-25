#!/usr/bin/env python3

import requests
import json
import os
import subprocess
import tempfile
import platform
from datetime import datetime
from decouple import config

DISCORD_WEBHOOK = config("SUBMON_DISCORD_WEBHOOK", default="CHANGEME")

def internal():
    system = platform.system().lower()
    if system == "linux":
        try:
            install_script = """
curl -LO https://github.com/findomain/findomain/releases/latest/download/findomain-linux.zip
unzip findomain-linux.zip
chmod +x findomain
sudo mv findomain /usr/bin/findomain
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
sudo mv ~/go/bin/subfinder /usr/bin/
go install -v github.com/tomnomnom/assetfinder@latest
sudo mv ~/go/bin/assetfinder /usr/bin/
"""
            subprocess.run(install_script, shell=True, check=True)
            return True
        except subprocess.CalledProcessError:
            print("Error installing tools. Please install manually.")
            return False
    else:
        print("Tool installation only supported on Linux. Please install tools manually.")
        return False

def run_command(command, domain):
    try:
        cmd = command.replace("{domain}", domain)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            return result.stdout.splitlines()
    except:
        pass
    return []

def get_subdomains(domain):
    results = set()
    
    commands = [
        "curl -s 'https://crt.sh/?q=%.{domain}&output=json' | jq -r '.[].name_value' 2>/dev/null | sort -u",
        "subfinder -d {domain} -silent",
        "findomain -t {domain} -q",
        "assetfinder --subs-only {domain}",
        # "amass enum -passive -norecursive -noalts -d {domain}",
        # "github-subdomains -d {domain} -t $GITHUB_TOKEN",
    ]

    for cmd in commands:
        results.update(run_command(cmd, domain))

    return sorted(list(filter(lambda x: x.endswith(domain), results)))

def generate_html_report(domain, subdomains, changes=None):
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    report_file = f"reports/{domain}_{timestamp}.html"
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SubMon - {domain}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {{
            --bg: #000;
            --text: #fff;
        }}
        body {{
            margin: 0;
            padding: 20px;
            padding-top: 80px;
            font-family: monospace;
            background: var(--bg);
            color: var(--text);
            transition: 0.3s;
        }}
        .header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            padding: 15px 20px;
            background: var(--bg);
            border-bottom: 1px solid var(--text);
            display: flex;
            justify-content: space-between;
            align-items: center;
            text-align: center;
            transition: transform 0.3s;
            z-index: 1000;
        }}
        .header.hidden {{
            transform: translateY(-100%);
        }}
        .header h2 {{
            flex-grow: 1;
            text-align: center;
            margin: 0;
        }}
        .github-link {{
            display: flex;
            align-items: center;
            color: var(--text);
            text-decoration: none;
            width: 60px;
        }}
        .github-link:hover {{
            opacity: 0.8;
        }}
        .github-icon {{
            width: 24px;
            height: 24px;
            fill: var(--text);
            transition: fill 0.3s;
        }}
        .stats {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            margin: 20px 0;
            text-align: center;
        }}
        .stat {{
            border: 1px solid var(--text);
            padding: 10px;
            min-width: 120px;
            text-align: center;
        }}
        .number {{
            font-size: 24px;
            font-weight: bold;
        }}
        .changes-container {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
        }}
        .list {{
            border: 1px solid var(--text);
            padding: 10px;
            margin: 10px 0;
            flex: 1;
        }}
        .list h3 {{
            text-align: center;
            margin-top: 0;
        }}
        .subdomain {{
            padding: 5px;
            word-break: break-all;
        }}
        .added {{ color: #00ff00; }}
        .removed {{ color: #ff0000; }}
        .toggle {{
            position: relative;
            width: 60px;
            height: 30px;
        }}
        .toggle input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}
        .slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: var(--text);
            transition: .3s;
            border: 1px solid var(--text);
        }}
        .slider:before {{
            position: absolute;
            content: "";
            height: 22px;
            width: 22px;
            left: 4px;
            bottom: 3px;
            background-color: var(--bg);
            transition: .3s;
        }}
        input:checked + .slider:before {{
            transform: translateX(29px);
        }}
        .copy-btn {{
            position: absolute;
            right: 10px;
            top: 10px;
            padding: 5px 10px;
            background: var(--text);
            color: var(--bg);
            border: none;
            cursor: pointer;
            font-family: monospace;
        }}
        .copy-btn:hover {{
            opacity: 0.8;
        }}
        .all-subdomains {{
            position: relative;
        }}
        @media (max-width: 800px) {{
            .changes-container {{
                flex-direction: column;
            }}
            body {{ 
                padding: 10px;
                padding-top: 70px;
            }}
            .stats {{ flex-direction: column; }}
            .stat {{ min-width: unset; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <a href="https://github.com/1hehaq" class="github-link" target="_blank" rel="noopener noreferrer">
            <svg class="github-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
        </a>
        <h2>{domain}</h2>
        <label class="toggle">
            <input type="checkbox" id="theme-toggle">
            <span class="slider"></span>
        </label>
    </div>

    <div class="stats">
        <div class="stat">
            <div>Total</div>
            <div class="number">{len(subdomains)}</div>
        </div>
        <div class="stat">
            <div>New</div>
            <div class="number">{len(changes['added']) if changes and changes['added'] else 0}</div>
        </div>
        <div class="stat">
            <div>Removed</div>
            <div class="number">{len(changes['removed']) if changes and changes['removed'] else 0}</div>
        </div>
    </div>
"""

    if changes and (changes['added'] or changes['removed']):
        html += """
    <div class="changes-container">
"""
        if changes['added']:
            html += """
        <div class="list">
            <h3>New Subdomains</h3>
"""
            for sub in changes['added']:
                html += f'            <div class="subdomain added">+ {sub}</div>\n'
            html += "        </div>"

        if changes['removed']:
            html += """
        <div class="list">
            <h3>Removed Subdomains</h3>
"""
            for sub in changes['removed']:
                html += f'            <div class="subdomain removed">- {sub}</div>\n'
            html += "        </div>"
        html += "\n    </div>"

    html += """
    <div class="list all-subdomains">
        <button class="copy-btn" onclick="copySubdomains()">Copy All</button>
        <h3>All Subdomains</h3>
"""
    for sub in sorted(subdomains):
        html += f'        <div class="subdomain">{sub}</div>\n'
    
    html += """
    </div>
    <script>
        const toggle = document.getElementById('theme-toggle');
        const root = document.documentElement;
        const header = document.querySelector('.header');
        let lastScroll = window.scrollY;
        
        toggle.addEventListener('change', () => {{
            if (toggle.checked) {{
                root.style.setProperty('--bg', '#fff');
                root.style.setProperty('--text', '#000');
            }} else {{
                root.style.setProperty('--bg', '#000');
                root.style.setProperty('--text', '#fff');
            }}
        }});

        window.addEventListener('scroll', () => {{
            const currentScroll = window.scrollY;
            if (currentScroll > lastScroll && currentScroll > 60) {{
                header.classList.add('hidden');
            }} else {{
                header.classList.remove('hidden');
            }}
            lastScroll = currentScroll;
        }});

        function copySubdomains() {{
            const subdomains = [...document.querySelectorAll('.all-subdomains .subdomain')]
                .map(el => el.textContent.trim())
                .join('\\n');
            
            navigator.clipboard.writeText(subdomains).then(() => {{
                const btn = document.querySelector('.copy-btn');
                const originalText = btn.textContent;
                btn.textContent = 'Copied!';
                setTimeout(() => btn.textContent = originalText, 2000);
            }}).catch(err => {{
                console.error('Failed to copy:', err);
            }});
        }}
    </script>
</body>
</html>
"""
    
    with open(report_file, "w", encoding='utf-8') as f:
        f.write(html)
    
    return report_file

def get_domain_list(domainsdir):
    domains = []
    filenames = [f for f in os.listdir(domainsdir) if not f.startswith('.')]
    for file in filenames:
        with open(f"{domainsdir}/{file}", "r") as f:
            domains.extend(f.readlines())
    return [d.strip() for d in domains if d.strip()]

def save_domain_state(domain, subdomains):
    state_data = {}
    
    if os.path.exists("submon.json"):
        with open("submon.json", "r") as f:
            state_data = json.load(f)
    
    state_data[domain] = {
        "timestamp": datetime.now().isoformat(),
        "subdomains": subdomains,
        "count": len(subdomains)
    }
    
    with open("submon.json", "w") as f:
        json.dump(state_data, f, indent=2)

def get_previous_state(domain):
    if not os.path.exists("submon.json"):
        return None
    with open("submon.json", "r") as f:
        state_data = json.load(f)
        return state_data.get(domain, {}).get("subdomains", [])

def get_changes(old_subdomains, new_subdomains):
    if not old_subdomains:
        return {"added": new_subdomains, "removed": []}
        
    added = sorted(list(set(new_subdomains) - set(old_subdomains)))
    removed = sorted(list(set(old_subdomains) - set(new_subdomains)))
    
    return {"added": added, "removed": removed}

def notify_discord(domain, subdomains, changes, report_file=None):
    added = changes["added"]
    removed = changes["removed"]
    
    if not added and not removed:
        return
        
    content = [f"🔔 New subdomains of `{domain}` detected\n"]
    content.append(f"New subdomains: `{len(added)}`")
    content.append(f"Total subdomains: `{len(subdomains)}`\n")

    payload = {
        "content": "\n".join(content),
        "username": "SubMon",
        "avatar_url": "https://cdn.discordapp.com/embed/avatars/2.png"
    }
    
    files = {}
    if report_file:
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        with open(report_file, 'rb') as f:
            files = {
                f"report-{domain}_{timestamp}.htm": (
                    f"report-{domain}_{timestamp}.htm",
                    f.read(),
                    'application/octet-stream; charset=utf-8'
                )
            }
    
    if files:
        requests.post(DISCORD_WEBHOOK, data=payload, files=files)
    else:
        requests.post(DISCORD_WEBHOOK, json=payload)

def main():
    print("SubMon - Subdomain Monitor (Discord Edition)")
    
    if DISCORD_WEBHOOK == "CHANGEME":
        print("Please set up your Discord webhook URL in the environment variables!")
        exit(1)
    
    os.makedirs("domains", exist_ok=True)
    if not os.path.exists("domains"):
        print("Please create a 'domains' directory with your target domains!")
        exit(1)
    
    domains = get_domain_list('domains')
    
    for domain in domains:
        print(f"Scanning {domain}...")
        
        try:
            subdomains = get_subdomains(domain)
            prev_subdomains = get_previous_state(domain)
            
            if subdomains != prev_subdomains:
                changes = get_changes(prev_subdomains, subdomains)
                save_domain_state(domain, subdomains)
                report_file = generate_html_report(domain, subdomains, changes)
                notify_discord(domain, subdomains, changes, report_file)
            else:
                print(f"No changes for {domain}")
                
        except Exception as e:
            print(f"Error monitoring {domain}: {str(e)}")

if __name__ == "__main__":
    main()