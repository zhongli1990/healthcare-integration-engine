// Global variables
let network = null;

// Initialize the application when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the visualization
    initVisualization();
    
    // Set up form submission
    document.getElementById('importForm').addEventListener('submit', handleImportSubmit);
    
    // Load components when the tab is shown
    document.getElementById('components-tab').addEventListener('shown.bs.tab', loadComponents);
    
    // Load visualization when the tab is shown
    document.getElementById('visualize-tab').addEventListener('shown.bs.tab', loadVisualization);
});

// Initialize the visualization
function initVisualization() {
    const container = document.getElementById('graph');
    const data = {
        nodes: new vis.DataSet([]),
        edges: new vis.DataSet([])
    };
    
    const options = {
        nodes: {
            shape: 'dot',
            size: 16,
            font: {
                size: 12,
                color: '#000000'
            },
            borderWidth: 2
        },
        edges: {
            width: 2,
            smooth: {
                type: 'continuous'
            },
            arrows: {
                to: {enabled: true, scaleFactor: 0.5}
            }
        },
        physics: {
            stabilization: false,
            barnesHut: {
                gravitationalConstant: -80000,
                springConstant: 0.001,
                springLength: 200
            }
        },
        interaction: {
            tooltipDelay: 200,
            hideEdgesOnDrag: true
        }
    };
    
    network = new vis.Network(container, data, options);
}

// Handle import form submission
async function handleImportSubmit(event) {
    event.preventDefault();
    
    const importStatus = document.getElementById('importStatus');
    const importButton = document.querySelector('#importForm button[type="submit"]');
    const originalButtonText = importButton.innerHTML;
    
    try {
        // Disable the button and show loading state
        importButton.disabled = true;
        importButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...';
        
        importStatus.innerHTML = `
            <div class="alert alert-info">
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm me-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <span>Uploading files and starting import process...</span>
                </div>
                <div class="progress mt-2" style="height: 5px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 0%"></div>
                </div>
                <div id="importProgress" class="small mt-1 text-muted">Preparing to upload...</div>
            </div>
        `;
        
        const progressElement = document.querySelector('#importStatus .progress-bar');
        const progressText = document.getElementById('importProgress');
        
        // Update progress
        const updateProgress = (percent, message) => {
            if (progressElement) {
                progressElement.style.width = `${percent}%`;
                progressElement.setAttribute('aria-valuenow', percent);
            }
            if (progressText) {
                progressText.textContent = message;
            }
        };
        
        updateProgress(10, 'Uploading files...');
        
        // Upload files
        const productionFile = document.getElementById('productionFile').files[0];
        const routingRuleFile = document.getElementById('routingRuleFile').files[0];
        
        const formData = new FormData();
        formData.append('production_file', productionFile);
        formData.append('routing_rule_file', routingRuleFile);
        
        const uploadResponse = await fetch('/api/imports/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.detail || 'File upload failed');
        }
        
        updateProgress(30, 'Files uploaded. Starting import process...');
        
        const uploadResult = await uploadResponse.json();
        
        // Get Neo4j connection details
        const neo4jUri = document.getElementById('neo4jUri').value;
        const neo4jUser = document.getElementById('neo4jUser').value;
        const neo4jPassword = document.getElementById('neo4jPassword').value;
        
        // Start the import
        const importResponse = await fetch('/api/imports', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                production_file: uploadResult.production_file,
                routing_rule_file: uploadResult.routing_rule_file,
                neo4j_uri: neo4jUri,
                neo4j_user: neo4jUser,
                neo4j_password: neo4jPassword
            })
        });
        
        if (!importResponse.ok) {
            const error = await importResponse.json();
            throw new Error(error.detail || 'Failed to start import');
        }
        
        updateProgress(50, 'Import started. Processing files...');
        
        const result = await importResponse.json();
        const importId = result.import_id;
        
        // Poll for import status
        return new Promise((resolve, reject) => {
            const checkStatus = async () => {
                try {
                    const statusResponse = await fetch(`/api/imports/${importId}`);
                    
                    if (!statusResponse.ok) {
                        throw new Error('Failed to check import status');
                    }
                    
                    const statusData = await statusResponse.json();
                    
                    // Update progress based on status
                    switch (statusData.status) {
                        case 'in_progress':
                            updateProgress(70, 'Import in progress...');
                            setTimeout(checkStatus, 1000);
                            break;
                            
                        case 'completed':
                            updateProgress(100, 'Import completed successfully!');
                            importStatus.innerHTML = `
                                <div class="alert alert-success">
                                    <h5><i class="bi bi-check-circle-fill"></i> Import Successful!</h5>
                                    <p>${statusData.message}</p>
                                    <p>Components imported: ${statusData.details?.components_imported || 0}</p>
                                    <p>Routing rules imported: ${statusData.details?.routing_rules_imported || 0}</p>
                                    <p class="mb-0">Relationships created: ${statusData.details?.relationships_created || 0}</p>
                                </div>
                            `;
                            
                            // Switch to visualization tab and reload data
                            const visualizeTab = new bootstrap.Tab(document.getElementById('visualize-tab'));
                            visualizeTab.show();
                            loadVisualization();
                            loadComponents();
                            
                            // Reset form
                            document.getElementById('importForm').reset();
                            importButton.disabled = false;
                            importButton.innerHTML = originalButtonText;
                            resolve();
                            break;
                            
                        case 'failed':
                            throw new Error(statusData.message || 'Import failed');
                            
                        default:
                            setTimeout(checkStatus, 1000);
                    }
                } catch (error) {
                    reject(error);
                }
            };
            
            // Start polling
            checkStatus();
        });
        
    } catch (error) {
        console.error('Import error:', error);
        importStatus.innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="bi bi-exclamation-triangle-fill"></i> Import Failed</h5>
                <p class="mb-0">${error.message}</p>
            </div>
        `;
        
        // Re-enable the button
        importButton.disabled = false;
        importButton.innerHTML = originalButtonText;
    }
}

// Format properties for display
function formatProperties(properties) {
    if (!properties || Object.keys(properties).length === 0) {
        return '<em>No properties</em>';
    }
    return Object.entries(properties)
        .map(([key, value]) => `<strong>${key}:</strong> ${JSON.stringify(value)}`)
        .join('<br>');
}

// Load components and relationships into their respective tables
async function loadComponents() {
    const componentsTbody = document.getElementById('componentsTableBody');
    const relationshipsTbody = document.getElementById('relationshipsTableBody');
    
    // Show loading state
    componentsTbody.innerHTML = '<tr><td colspan="5" class="text-center">Loading components...</td></tr>';
    relationshipsTbody.innerHTML = '<tr><td colspan="4" class="text-center">Loading relationships...</td></tr>';
    
    try {
        const response = await fetch('/api/visualizations/components');
        if (!response.ok) {
            throw new Error('Failed to load components and relationships');
        }
        
        const data = await response.json();
        const { components = [], relationships = [] } = data;
        
        // Render components table
        if (components.length === 0) {
            componentsTbody.innerHTML = '<tr><td colspan="5" class="text-center">No components found</td></tr>';
        } else {
            componentsTbody.innerHTML = components.map(comp => `
                <tr>
                    <td><code>${comp.id}</code></td>
                    <td>${comp.name || '<em>Unnamed</em>'}</td>
                    <td><span class="badge bg-primary">${comp.type || 'Unknown'}</span></td>
                    <td><span class="badge bg-success">${comp.status || 'Active'}</span></td>
                    <td>${formatProperties(comp.properties)}</td>
                </tr>
            `).join('');
        }
        
        // Render relationships table
        renderRelationships(relationships);
        
    } catch (error) {
        console.error('Error loading components and relationships:', error);
        componentsTbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-danger">
                    Error loading components: ${error.message}
                </td>
            </tr>`;
        relationshipsTbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-danger">
                    Error loading relationships: ${error.message}
                </td>
            </tr>`;
    }
}

// Render relationships in the relationships table
function renderRelationships(relationships) {
    const tbody = document.getElementById('relationshipsTableBody');
    
    if (!relationships || relationships.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No relationships found</td></tr>';
        return;
    }
    
    tbody.innerHTML = relationships.map(rel => {
        const source = rel.source || {};
        const target = rel.target || {};
        const type = rel.type || 'UNKNOWN';
        const properties = rel.properties || {};
        
        return `
            <tr>
                <td>
                    <div><strong>${source.name || 'Unnamed'}</strong></div>
                    <small class="text-muted">${source.type || 'Unknown'}</small>
                </td>
                <td>
                    <span class="badge bg-info">${type}</span>
                </td>
                <td>
                    <div><strong>${target.name || 'Unnamed'}</strong></div>
                    <small class="text-muted">${target.type || 'Unknown'}</small>
                </td>
                <td>${formatProperties(properties)}</td>
            </tr>
        `;
    }).join('');
}

// Load visualization data
async function loadVisualization() {
    try {
        const response = await fetch('/api/visualizations/graph');
        if (!response.ok) {
            throw new Error('Failed to load visualization data');
        }
        
        const data = await response.json();
        
        // Transform data for vis.js
        const nodes = new vis.DataSet(
            data.nodes.map(node => ({
                id: node.id,
                label: node.label,
                group: node.type,
                title: `Type: ${node.type}\n${JSON.stringify(node.properties, null, 2)}`
            }))
        );
        
        const edges = new vis.DataSet(
            data.links.map(link => ({
                from: link.source,
                to: link.target,
                label: link.type,
                title: JSON.stringify(link.properties, null, 2)
            }))
        );
        
        // Update the network
        network.setData({
            nodes: nodes,
            edges: edges
        });
        
        // Fit the network to show all nodes
        network.fit({
            animation: {
                duration: 500,
                easingFunction: 'easeInOutQuad'
            }
        });
        
    } catch (error) {
        console.error('Error loading visualization:', error);
    }
}
