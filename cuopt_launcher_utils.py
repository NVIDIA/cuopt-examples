"""
cuOpt Examples Launcher Utilities

This module contains all helper functions for the cuopt_examples_launcher notebook.
"""

import os
import sys
from pathlib import Path
import subprocess
from IPython.display import display, HTML, Markdown, clear_output
import ipywidgets as widgets
from ipywidgets import Button, VBox, HBox, Output, Dropdown, Layout, HTML as HTMLWidget

# Configuration
REPO_URL = "https://github.com/NVIDIA/cuopt-examples.git"
DEFAULT_BRANCH = "branch-25.10"
REPO_NAME = "cuopt-examples"

# Detect if running in Colab
IN_COLAB = 'google.colab' in sys.modules

if IN_COLAB:
    BASE_DIR = Path("/content")
else:
    BASE_DIR = Path.cwd()

REPO_PATH = BASE_DIR / REPO_NAME


# ============================================================================
# Git and Command Execution
# ============================================================================

def run_command(command, cwd=None):
    """Execute a shell command and return output"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=cwd
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def clone_or_update_repo():
    """Clone repository if it doesn't exist, otherwise update it"""
    if REPO_PATH.exists():
        print("📂 Repository found. Fetching latest changes...")
        success, stdout, stderr = run_command("git fetch --all", cwd=REPO_PATH)
        if success:
            print("✅ Repository updated!")
        else:
            print(f"⚠️  Warning: {stderr}")
    else:
        print(f"📥 Cloning repository...")
        success, stdout, stderr = run_command(f"git clone {REPO_URL} {REPO_PATH}")
        if success:
            print("✅ Repository cloned successfully!")
        else:
            print(f"❌ Error: {stderr}")
            return
    
    # Show current branch
    success, current_branch, _ = run_command("git branch --show-current", cwd=REPO_PATH)
    if success:
        print(f"🌿 Current branch: {current_branch.strip()}")


# ============================================================================
# Branch Management
# ============================================================================

def get_available_branches():
    """Get list of all available branches"""
    success, stdout, stderr = run_command("git branch -a", cwd=REPO_PATH)
    if not success:
        return [DEFAULT_BRANCH]
    
    branches = []
    for line in stdout.split('\n'):
        line = line.strip()
        if line and not line.startswith('*'):
            # Remove remote prefix and clean up
            if 'remotes/origin/' in line:
                branch = line.replace('remotes/origin/', '').strip()
                if branch and '->' not in branch and branch not in branches:
                    branches.append(branch)
            elif line:
                branch = line.strip('* ')
                if branch not in branches:
                    branches.append(branch)
    
    return sorted(set(branches)) if branches else [DEFAULT_BRANCH]


def switch_branch(branch_name):
    """Switch to a different branch"""
    print(f"🔄 Switching to branch: {branch_name}...")
    
    # Fetch latest changes
    run_command("git fetch --all", cwd=REPO_PATH)
    
    # Try to checkout the branch
    success, stdout, stderr = run_command(f"git checkout {branch_name}", cwd=REPO_PATH)
    
    if success:
        # Pull latest changes
        run_command("git pull", cwd=REPO_PATH)
        print(f"✅ Successfully switched to branch: {branch_name}")
    else:
        print(f"❌ Error switching branch: {stderr}")


def create_branch_selector():
    """Create branch selector UI"""
    branches = get_available_branches()
    
    # Get current branch
    success, current_branch, _ = run_command("git branch --show-current", cwd=REPO_PATH)
    current = current_branch.strip() if success else DEFAULT_BRANCH
    
    branch_dropdown = Dropdown(
        options=branches,
        value=current if current in branches else (branches[0] if branches else DEFAULT_BRANCH),
        description='Branch:',
        style={'description_width': 'initial'},
        layout=Layout(width='400px')
    )
    
    switch_button = Button(
        description='Switch Branch',
        button_style='info',
        icon='exchange',
        layout=Layout(width='150px')
    )
    
    output = Output()
    
    def on_switch_click(b):
        output.clear_output()
        with output:
            switch_branch(branch_dropdown.value)
    
    switch_button.on_click(on_switch_click)
    
    return VBox([
        HBox([branch_dropdown, switch_button]),
        output
    ])


# ============================================================================
# Notebook Scanning and Management
# ============================================================================

def scan_notebooks(base_path):
    """Scan directory for all notebooks and organize by folder"""
    notebooks = {}
    base = Path(base_path)
    
    if not base.exists():
        return notebooks
    
    for nb_file in base.rglob('*.ipynb'):
        # Skip hidden files and checkpoints
        if any(part.startswith('.') for part in nb_file.parts):
            continue
        
        # Get relative path
        rel_path = nb_file.relative_to(base)
        folder = rel_path.parent.as_posix() if rel_path.parent != Path('.') else 'root'
        
        if folder not in notebooks:
            notebooks[folder] = []
        
        notebooks[folder].append({
            'name': nb_file.name,
            'path': rel_path.as_posix(),
            'full_path': nb_file
        })
    
    # Sort notebooks within each folder
    for folder in notebooks:
        notebooks[folder] = sorted(notebooks[folder], key=lambda x: x['name'])
    
    return notebooks


def get_colab_url(notebook_path, branch='main'):
    """Generate Google Colab URL for a notebook"""
    github_path = f"NVIDIA/cuopt-examples/blob/{branch}/{notebook_path}"
    return f"https://colab.research.google.com/github/{github_path}"


def get_setup_code(notebook_path, branch='main'):
    """Generate setup code to run in Colab for accessing data files"""
    folder = str(Path(notebook_path).parent)
    setup_code = f"""# ============================================================================
# Setup code for Google Colab
# ============================================================================
# IMPORTANT: 
# 1. Run this code BEFORE any other code in the notebook!
# 2. Re-run this every time you restart your Colab session!
# ============================================================================

import os
from pathlib import Path

# Clone the repository if not already present
if not Path('/content/cuopt-examples').exists():
    !git clone https://github.com/NVIDIA/cuopt-examples.git
    %cd /content/cuopt-examples
    !git checkout {branch}
else:
    %cd /content/cuopt-examples
    !git pull

# Navigate to notebook directory
%cd /content/cuopt-examples/{folder}

# Install requirements if available
if Path('requirements.txt').exists():
    %pip install -r requirements.txt -q
elif Path('../requirements.txt').exists():
    %pip install -r ../requirements.txt -q

print("✅ Setup complete! All data files and dependencies are now available.")
"""
    return setup_code


def get_readme_content(folder_path):
    """Get README content for a folder if it exists"""
    readme_path = folder_path / "README.md"
    if readme_path.exists():
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Limit to first 500 characters for preview
                if len(content) > 500:
                    content = content[:500] + "..."
                return content
        except Exception as e:
            return None
    return None


def escape_html(text):
    """Escape HTML special characters"""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))


# ============================================================================
# Widget Creation
# ============================================================================

def create_notebook_item(nb, branch):
    """Create a widget for a single notebook with setup code display"""
    from ipywidgets import Textarea, ToggleButton, VBox as VB, HBox as HB, Label
    
    colab_url = get_colab_url(nb['path'], branch)
    setup_code = get_setup_code(nb['path'], branch)
    
    # Create toggle button for showing setup code
    toggle_btn = ToggleButton(
        value=False,
        description='📋 Show Setup Code',
        button_style='',  # Custom styling below
        tooltip='Click to show/hide setup code for Colab',
        layout=Layout(width='180px'),
        style={'button_color': '#76B900', 'font_weight': 'bold'}
    )
    
    # Create textarea with setup code (initially hidden)
    code_textarea = Textarea(
        value=setup_code,
        placeholder='',
        description='',
        disabled=False,
        layout=Layout(width='100%', height='250px', visibility='hidden')
    )
    
    instruction_label = Label(
        value='👇 Copy this code (Ctrl+A / Cmd+A, then Ctrl+C / Cmd+C). ⚠️ Run BEFORE any other code & after each session restart!',
        layout=Layout(visibility='hidden')
    )
    
    # Toggle visibility
    def on_toggle(change):
        if change['new']:
            code_textarea.layout.visibility = 'visible'
            instruction_label.layout.visibility = 'visible'
            toggle_btn.description = '🔼 Hide Setup Code'
        else:
            code_textarea.layout.visibility = 'hidden'
            instruction_label.layout.visibility = 'hidden'
            toggle_btn.description = '📋 Show Setup Code'
    
    toggle_btn.observe(on_toggle, names='value')
    
    # Create the notebook item
    colab_link = HTMLWidget(f"""
        <a href='{colab_url}' target='_blank' style='text-decoration: none;'>
            <button style='background-color: #F9AB00; color: white; border: none; padding: 8px 16px; 
                           border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px;'>
                <img src='https://colab.research.google.com/img/colab_favicon_256px.png' 
                     width='16' height='16' style='vertical-align: middle; margin-right: 5px;'>
                Open in Colab
            </button>
        </a>
    """)
    
    header = HTMLWidget(f"""
        <div style='padding: 5px;'>
            <strong style='font-size: 14px; color: #333;'>📓 {nb['name']}</strong>
            <div style='font-size: 11px; color: #666; margin-top: 3px;'>{nb['path']}</div>
            <div style='font-size: 11px; color: #d9534f; margin-top: 5px; font-weight: 600; 
                        background-color: #fff3cd; padding: 4px 8px; border-radius: 4px; border-left: 3px solid #d9534f;'>
                ⚠️ GPU Required: Runtime → Change Runtime Type → Hardware accelerator: GPU
            </div>
        </div>
    """)
    
    return VB([
        HB([header, colab_link, toggle_btn], layout=Layout(justify_content='space-between', align_items='center')),
        instruction_label,
        code_textarea
    ], layout=Layout(
        padding='12px',
        margin='8px 0',
        border='1px solid #d0e8b8',
        border_radius='6px',
        background_color='#fafffe'
    ))


def create_notebook_browser():
    """Create interactive notebook browser with Colab links"""
    notebooks = scan_notebooks(REPO_PATH)
    
    if not notebooks:
        return HTMLWidget("<p style='color: red;'>No notebooks found. Please clone the repository first.</p>")
    
    # Get current branch for Colab links
    success, current_branch, _ = run_command("git branch --show-current", cwd=REPO_PATH)
    branch = current_branch.strip() if success else DEFAULT_BRANCH
    
    # Create accordion for folders
    accordion_items = []
    accordion_titles = []
    
    for folder in sorted(notebooks.keys()):
        folder_notebooks = notebooks[folder]
        
        # Create widgets list for this folder
        folder_widgets = []
        
        # Add README if available
        folder_path = REPO_PATH / folder if folder != 'root' else REPO_PATH
        readme = get_readme_content(folder_path)
        if readme:
            readme_widget = HTMLWidget(f"""
            <div style='background-color: #f0f9e8; padding: 12px; margin-bottom: 15px; 
                        border-radius: 6px; border-left: 4px solid #76B900;'>
                <strong style='color: #2d5016;'>📖 Folder Description:</strong>
                <pre style='white-space: pre-wrap; font-size: 12px; margin-top: 5px; 
                     color: #2d5016; background: transparent; border: none; padding: 0;'>{escape_html(readme)}</pre>
            </div>
            """)
            folder_widgets.append(readme_widget)
        
        # Add each notebook as a widget
        for nb in folder_notebooks:
            nb_widget = create_notebook_item(nb, branch)
            folder_widgets.append(nb_widget)
        
        # Create VBox for this folder
        folder_vbox = VBox(folder_widgets, layout=Layout(padding='10px'))
        accordion_items.append(folder_vbox)
        
        # Format folder title with NVIDIA green styling
        nb_count = len(folder_notebooks)
        folder_display = folder.replace('_', ' ').title() if folder != 'root' else 'Root'
        accordion_titles.append(f"🟢 {folder_display} ({nb_count} notebook{'s' if nb_count != 1 else ''})")
    
    # Create elegant accordion with NVIDIA green styling
    accordion = widgets.Accordion(
        children=accordion_items,
        layout=Layout(
            border='2px solid #76B900',
            border_radius='8px',
            margin='10px 0',
            overflow='hidden'
        )
    )
    for i, title in enumerate(accordion_titles):
        accordion.set_title(i, title)
    
    # Summary with NVIDIA green branding
    total_notebooks = sum(len(nbs) for nbs in notebooks.values())
    summary = HTMLWidget(f"""
    <style>
        .p-Accordion-child {{
            border-top: 2px solid #76B900 !important;
        }}
        .p-Collapse-header {{
            background-color: #f0f9e8 !important;
            font-weight: 600 !important;
            color: #2d5016 !important;
        }}
        .p-Collapse-header:hover {{
            background-color: #e1f2d4 !important;
        }}
        .p-Collapse-open > .p-Collapse-header {{
            background-color: #76B900 !important;
            color: white !important;
        }}
    </style>
    <div style='background: linear-gradient(135deg, #76B900 0%, #5a9200 100%); 
                color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <h3 style='margin: 0 0 10px 0; font-weight: 600;'>📚 Notebook Library</h3>
        <p style='margin: 0; font-size: 15px; opacity: 0.95;'>
            Found <strong>{total_notebooks}</strong> notebooks across <strong>{len(notebooks)}</strong> categories
        </p>
        <p style='margin: 8px 0 0 0; font-size: 13px; opacity: 0.9;'>
            Current branch: <strong>{branch}</strong>
        </p>
    </div>
    <div style='background-color: #f0f9e8; border: 2px solid #76B900; border-radius: 8px; 
                padding: 18px; margin-bottom: 20px;'>
        <h4 style='margin: 0 0 12px 0; color: #2d5016;'>
            💡 Running Notebooks in Google Colab
        </h4>
        <div style='background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 12px; border-radius: 4px;'>
            <strong style='color: #856404; font-size: 13px;'>⚠️ GPU Required:</strong>
            <span style='color: #856404; font-size: 13px;'> These notebooks require a GPU. By default, Colab runs on a non-GPU instance. You must change this!</span>
        </div>
        <div style='margin-bottom: 12px;'>
            <strong style='color: #2d5016; font-size: 13px;'>Step 1: Enable GPU (Required)</strong>
            <p style='margin: 4px 0 0 0; font-size: 13px; color: #2d5016; line-height: 1.5;'>
                Go to <strong>Runtime → Change Runtime Type</strong> and set <strong>Hardware accelerator</strong> to <strong>GPU</strong> (select one of the available GPUs)
            </p>
        </div>
        <div>
            <strong style='color: #2d5016; font-size: 13px;'>Step 2: Setup Data Files (Required)</strong>
            <p style='margin: 4px 0 0 0; font-size: 13px; color: #2d5016; line-height: 1.5;'>
                Click <span style='background-color: #76B900; color: white; 
                padding: 2px 6px; border-radius: 3px; font-size: 11px;'>📋 Show Setup Code</span>, 
                copy it, paste it in a new cell at the top of your notebook, and run it BEFORE any other code
            </p>
        </div>
    </div>
    """)
    
    return VBox([summary, accordion])


def create_quick_actions():
    """Create quick action buttons"""
    
    refresh_button = Button(
        description='🔄 Refresh Browser',
        button_style='success',
        layout=Layout(width='200px', height='40px')
    )
    
    update_repo_button = Button(
        description='📥 Pull Latest Changes',
        button_style='info',
        layout=Layout(width='200px', height='40px')
    )
    
    show_status_button = Button(
        description='ℹ️ Show Git Status',
        button_style='warning',
        layout=Layout(width='200px', height='40px')
    )
    
    output = Output()
    
    def on_refresh(b):
        output.clear_output()
        with output:
            print("🔄 Refreshing notebook browser...")
            display(create_notebook_browser())
    
    def on_update(b):
        output.clear_output()
        with output:
            print("📥 Pulling latest changes...")
            success, stdout, stderr = run_command("git pull", cwd=REPO_PATH)
            if success:
                print("✅ Repository updated successfully!")
                print(stdout)
            else:
                print(f"❌ Error: {stderr}")
    
    def on_status(b):
        output.clear_output()
        with output:
            print("📊 Git Status:")
            success, stdout, stderr = run_command("git status", cwd=REPO_PATH)
            if success:
                print(stdout)
            else:
                print(f"❌ Error: {stderr}")
            
            print("\n📝 Recent Commits:")
            success, stdout, stderr = run_command("git log --oneline -5", cwd=REPO_PATH)
            if success:
                print(stdout)
    
    refresh_button.on_click(on_refresh)
    update_repo_button.on_click(on_update)
    show_status_button.on_click(on_status)
    
    return VBox([
        HBox([refresh_button, update_repo_button, show_status_button], 
             layout=Layout(justify_content='space-around')),
        output
    ])


def display_interactive_ui():
    """Display the complete interactive UI with quick actions, branch selector, and notebook browser"""
    
    # Quick Actions at the top for easy access
    display(Markdown("### ⚡ Quick Actions"))
    
    # Create simplified quick actions for top
    refresh_button = Button(
        description='🔄 Refresh Browser',
        button_style='success',
        layout=Layout(width='180px', height='40px'),
        tooltip='Reload the notebook list'
    )
    
    update_repo_button = Button(
        description='📥 Pull Latest Changes',
        button_style='info',
        layout=Layout(width='180px', height='40px'),
        tooltip='Update repository from remote'
    )
    
    show_status_button = Button(
        description='ℹ️ Show Git Status',
        button_style='warning',
        layout=Layout(width='180px', height='40px'),
        tooltip='Display git status and recent commits'
    )
    
    quick_output = Output()
    
    def on_refresh(b):
        quick_output.clear_output()
        with quick_output:
            print("🔄 Refreshing...")
            print("✅ To refresh, please re-run this cell (Shift+Enter)")
    
    def on_update(b):
        quick_output.clear_output()
        with quick_output:
            print("📥 Pulling latest changes...")
            success, stdout, stderr = run_command("git pull", cwd=REPO_PATH)
            if success:
                print("✅ Repository updated successfully!")
                print(stdout)
                print("\n💡 Re-run this cell to see updated notebooks")
            else:
                print(f"❌ Error: {stderr}")
    
    def on_status(b):
        quick_output.clear_output()
        with quick_output:
            print("📊 Git Status:")
            success, stdout, stderr = run_command("git status", cwd=REPO_PATH)
            if success:
                print(stdout)
            else:
                print(f"❌ Error: {stderr}")
            
            print("\n📝 Recent Commits:")
            success, stdout, stderr = run_command("git log --oneline -5", cwd=REPO_PATH)
            if success:
                print(stdout)
    
    refresh_button.on_click(on_refresh)
    update_repo_button.on_click(on_update)
    show_status_button.on_click(on_status)
    
    display(HBox([refresh_button, update_repo_button, show_status_button], 
                 layout=Layout(justify_content='flex-start', margin='10px 0')))
    display(quick_output)
    
    # Display Branch Selector
    display(Markdown("---"))
    display(Markdown("### 🌿 Select Branch"))
    display(create_branch_selector())
    
    # Display Notebook Browser
    display(Markdown("---"))
    display(Markdown("### 📚 Browse and Launch Notebooks"))
    display(create_notebook_browser())

