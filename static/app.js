let currentData = null;
let allEmployees = [];
let root = null;
let svg = null;
let g = null;
let zoom = null;
let appSettings = {};
let currentLayout = 'vertical'; // Default layout

const API_BASE_URL = window.location.origin;
const nodeWidth = 220;
const nodeHeight = 80;
const levelHeight = 120;
const userIconUrl = window.location.origin + '/static/usericon.png';

async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/settings`);
        if (response.ok) {
            appSettings = await response.json();
            applySettings();
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

function applySettings() {
    if (appSettings.chartTitle) {
        document.querySelector('.header-text h1').textContent = appSettings.chartTitle;
    }

    if (appSettings.headerColor) {
        const header = document.querySelector('.header');
        const darker = adjustColor(appSettings.headerColor, -30);
        header.style.background = `linear-gradient(135deg, ${appSettings.headerColor} 0%, ${darker} 100%)`;
    }

    if (appSettings.logoPath) {
        document.querySelector('.header-logo').src = appSettings.logoPath + '?t=' + Date.now();
    }

    if (appSettings.updateTime) {
        const timeText = appSettings.autoUpdateEnabled ? 
            `Updates daily @ ${convertTo12Hour(appSettings.updateTime)}` : 
            'Auto-update disabled';
        document.querySelector('.header-text p').textContent = timeText;
    }
}

function adjustColor(color, amount) {
    const num = parseInt(color.replace('#', ''), 16);
    const r = Math.max(0, Math.min(255, (num >> 16) + amount));
    const g = Math.max(0, Math.min(255, ((num >> 8) & 0x00FF) + amount));
    const b = Math.max(0, Math.min(255, (num & 0x0000FF) + amount));
    return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
}

function convertTo12Hour(time24) {
    const [hours, minutes] = time24.split(':');
    const h = parseInt(hours);
    const suffix = h >= 12 ? 'PM' : 'AM';
    const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${h12}:${minutes} ${suffix}`;
}

function setLayoutOrientation(orientation) {
    currentLayout = orientation;
    
    // Update button states
    document.querySelectorAll('.layout-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.closest('.layout-btn').classList.add('active');
    
    // Re-render the chart with new orientation
    if (root) {
        update(root);
        fitToScreen();
    }
}

async function init() {
    await loadSettings();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/employees`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        currentData = await response.json();
        
        if (currentData) {
            allEmployees = flattenTree(currentData);
            renderOrgChart(currentData);
        } else {
            throw new Error('No data received from server');
        }
    } catch (error) {
        console.error('Error loading employee data:', error);
        document.getElementById('orgChart').innerHTML = '<div class="loading">Error loading data. Please refresh the page.</div>';
    }
}

function flattenTree(node, list = []) {
    if (!node) return list;
    list.push(node);
    if (node.children && Array.isArray(node.children)) {
        node.children.forEach(child => flattenTree(child, list));
    }
    return list;
}

function renderOrgChart(data) {
    if (!data) {
        console.error('No data to render');
        return;
    }

    const container = document.getElementById('orgChart');
    container.querySelector('.loading').style.display = 'none';

    const width = container.clientWidth;
    const height = container.clientHeight || 800;

    svg = d3.select('#orgChart')
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    zoom = d3.zoom()
        .scaleExtent([0.1, 3])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });

    svg.call(zoom);

    g = svg.append('g');

    const initialTransform = d3.zoomIdentity.translate(width/2, 100);
    svg.call(zoom.transform, initialTransform);

    root = d3.hierarchy(data);

    root.x0 = 0;
    root.y0 = 0;

    const treeLayout = d3.tree()
        .nodeSize([nodeWidth + 20, levelHeight]);

    const collapseLevel = appSettings.collapseLevel || '2';
    if (collapseLevel !== 'all') {
        const level = parseInt(collapseLevel);
        root.each(d => {
            if (d.depth >= level - 1 && d.children) {
                d._children = d.children;
                d.children = null;
            }
        });
    }

    update(root);
}

function update(source) {
    const treeLayout = d3.tree()
        .nodeSize(currentLayout === 'vertical' 
            ? [nodeWidth + 20, levelHeight] 
            : [levelHeight, nodeWidth + 20]);

    const treeData = treeLayout(root);
    const nodes = treeData.descendants();
    const links = treeData.links();

    // Swap x and y coordinates for horizontal layout
    if (currentLayout === 'horizontal') {
        nodes.forEach(d => {
            const temp = d.x;
            d.x = d.y;
            d.y = temp;
        });
    }

    const link = g.selectAll('.link')
        .data(links, d => d.target.data.id);

    const linkEnter = link.enter()
        .insert('path', 'g')
        .attr('class', 'link')
        .attr('d', d => {
            const o = {x: source.x0 || source.x, y: source.y0 || source.y};
            return diagonal(o, o);
        });

    link.merge(linkEnter)
        .transition()
        .duration(500)
        .attr('d', d => diagonal(d.source, d.target));

    link.exit()
        .transition()
        .duration(500)
        .attr('d', d => {
            const o = {x: source.x, y: source.y};
            return diagonal(o, o);
        })
        .remove();

    const node = g.selectAll('.node')
        .data(nodes, d => d.data.id);

    const nodeEnter = node.enter()
        .append('g')
        .attr('class', d => d.depth === 0 ? 'node ceo' : 'node')
        .attr('transform', d => `translate(${source.x0 || source.x}, ${source.y0 || source.y})`)
        .on('click', (event, d) => {
            event.stopPropagation();
            showEmployeeDetail(d.data);
        });

    nodeEnter.append('rect')
        .attr('class', d => {
            let classes = 'node-rect';
            if (appSettings.highlightNewEmployees !== false && d.data.isNewEmployee) {
                classes += ' new-employee';
            }
            return classes;
        })
        .attr('x', -nodeWidth/2)
        .attr('y', -nodeHeight/2)
        .attr('width', nodeWidth)
        .attr('height', nodeHeight)
        .style('fill', d => {
            const nodeColors = appSettings.nodeColors || {};
            switch(d.depth) {
                case 0: return nodeColors.level0 || '#90EE90';
                case 1: return nodeColors.level1 || '#FFFFE0';
                case 2: return nodeColors.level2 || '#E0F2FF';
                case 3: return nodeColors.level3 || '#FFE4E1';
                case 4: return nodeColors.level4 || '#E8DFF5';
                case 5: return nodeColors.level5 || '#FFEAA7';
                default: return '#F0F0F0'; 
            }
        })
        .style('stroke', d => {
            if (appSettings.highlightNewEmployees !== false && d.data.isNewEmployee) {
                return null;
            }
            const nodeColors = appSettings.nodeColors || {};
            let fillColor;
            switch(d.depth) {
                case 0: fillColor = nodeColors.level0 || '#90EE90'; break;
                case 1: fillColor = nodeColors.level1 || '#FFFFE0'; break;
                case 2: fillColor = nodeColors.level2 || '#E0F2FF'; break;
                case 3: fillColor = nodeColors.level3 || '#FFE4E1'; break;
                case 4: fillColor = nodeColors.level4 || '#E8DFF5'; break;
                case 5: fillColor = nodeColors.level5 || '#FFEAA7'; break;
                default: fillColor = '#F0F0F0';
            }
            return adjustColor(fillColor, -50);
        })
        .style('stroke-width', '2px');

    if (appSettings.showProfileImages !== false) {
        nodeEnter.append('image')
            .attr('xlink:href', userIconUrl)
            .attr('x', -nodeWidth/2 + 10)
            .attr('y', -nodeHeight/2 + (nodeHeight - 50) / 2)
            .attr('width', 50)
            .attr('height', 50)
            .attr('clip-path', 'circle(25px at 25px 25px)')
            .attr('preserveAspectRatio', 'xMidYMid slice');
    }

    nodeEnter.append('text')
        .attr('class', 'node-text')
        .attr('x', appSettings.showProfileImages !== false ? nodeWidth/2 - 10 : 0)
        .attr('y', -20)
        .attr('text-anchor', appSettings.showProfileImages !== false ? 'end' : 'middle')
        .style('font-weight', 'bold')
        .text(d => {
            const name = d.data.name;
            return name.length > 22 ? name.substring(0, 22) + '...' : name;
        });

    nodeEnter.append('text')
        .attr('class', 'node-title')
        .attr('x', appSettings.showProfileImages !== false ? nodeWidth/2 - 10 : 0)
        .attr('y', -5)
        .attr('text-anchor', appSettings.showProfileImages !== false ? 'end' : 'middle')
        .text(d => {
            const title = d.data.title;
            return title.length > 28 ? title.substring(0, 28) + '...' : title;
        });

    if (appSettings.showDepartments !== false) {
        nodeEnter.append('text')
            .attr('class', 'node-department')
            .attr('x', appSettings.showProfileImages !== false ? nodeWidth/2 - 10 : 0)
            .attr('y', 25)
            .attr('text-anchor', appSettings.showProfileImages !== false ? 'end' : 'middle')
            .text(d => {
                const dept = d.data.department || 'Not specified';
                return dept.length > 28 ? dept.substring(0, 28) + '...' : dept;
            });
    }

    if (appSettings.showEmployeeCount !== false) {
        const countGroup = nodeEnter.append('g')
            .attr('class', 'count-badge')
            .style('display', d => {
                const totalCount = d._children?.length || d.children?.length || 0;
                return totalCount > 0 ? 'block' : 'none';
            });

        countGroup.append('circle')
            .attr('cx', -nodeWidth/2 + 15)
            .attr('cy', -nodeHeight/2 + 15)
            .attr('r', 12)
            .style('fill', '#ff6b6b')
            .style('stroke', 'white')
            .style('stroke-width', '2px');

        countGroup.append('text')
            .attr('x', -nodeWidth/2 + 15)
            .attr('y', -nodeHeight/2 + 19)
            .attr('text-anchor', 'middle')
            .style('fill', 'white')
            .style('font-size', '11px')
            .style('font-weight', 'bold')
            .text(d => {
                const count = d._children?.length || d.children?.length || 0;
                return count > 99 ? '99+' : count;
            });
    }

    const expandBtn = nodeEnter.append('g')
        .attr('class', 'expand-group')
        .style('display', d => (d._children?.length || d.children?.length) ? 'block' : 'none')
        .on('click', (event, d) => {
            event.stopPropagation();
            toggle(d);
        });

    expandBtn.append('circle')
        .attr('class', 'expand-btn')
        .attr('cy', currentLayout === 'vertical' ? nodeHeight/2 + 10 : 0)
        .attr('cx', currentLayout === 'horizontal' ? nodeWidth/2 + 10 : 0)
        .attr('r', 10);

    expandBtn.append('text')
        .attr('class', 'expand-text')
        .attr('y', currentLayout === 'vertical' ? nodeHeight/2 + 15 : 4)
        .attr('x', currentLayout === 'horizontal' ? nodeWidth/2 + 10 : 0)
        .attr('text-anchor', 'middle')
        .text(d => d._children?.length ? '+' : '-');

    if (appSettings.highlightNewEmployees !== false) {
        const newBadgeGroup = nodeEnter.append('g')
            .attr('class', 'new-employee-badge')
            .style('display', d => d.data.isNewEmployee ? 'block' : 'none');

        newBadgeGroup.append('rect')
            .attr('class', 'new-badge')
            .attr('x', nodeWidth/2 - 45)
            .attr('y', -nodeHeight/2 - 10)
            .attr('width', 35)
            .attr('height', 18)
            .attr('rx', 9)
            .attr('ry', 9);

        newBadgeGroup.append('text')
            .attr('class', 'new-badge-text')
            .attr('x', nodeWidth/2 - 27)
            .attr('y', -nodeHeight/2 + 2)
            .attr('text-anchor', 'middle')
            .text('NEW');
    }


    const nodeUpdate = node.merge(nodeEnter)
        .transition()
        .duration(500)
        .attr('transform', d => `translate(${d.x}, ${d.y})`);

    nodeUpdate.select('.expand-text')
        .text(d => d._children?.length ? '+' : '-')
        .attr('y', currentLayout === 'vertical' ? nodeHeight/2 + 15 : 4)
        .attr('x', currentLayout === 'horizontal' ? nodeWidth/2 + 10 : 0);

    nodeUpdate.select('.expand-btn')
        .attr('cy', currentLayout === 'vertical' ? nodeHeight/2 + 10 : 0)
        .attr('cx', currentLayout === 'horizontal' ? nodeWidth/2 + 10 : 0);

    nodeUpdate.select('.expand-group')
        .style('display', d => (d._children?.length || d.children?.length) ? 'block' : 'none');

    if (appSettings.showEmployeeCount !== false) {
        nodeUpdate.select('.count-badge')
            .style('display', d => {
                const totalCount = d._children?.length || d.children?.length || 0;
                return totalCount > 0 ? 'block' : 'none';
            });

        nodeUpdate.select('.count-badge text')
            .text(d => {
                const count = d._children?.length || d.children?.length || 0;
                return count > 99 ? '99+' : count;
            });
    }

    node.exit()
        .transition()
        .duration(500)
        .attr('transform', d => `translate(${source.x}, ${source.y})`)
        .remove();

    nodes.forEach(d => {
        d.x0 = d.x;
        d.y0 = d.y;
    });
}

function diagonal(s, d) {
    if (currentLayout === 'vertical') {
        const midY = (s.y + d.y) / 2;
        return `M ${s.x} ${s.y + nodeHeight/2}
                L ${s.x} ${midY}
                L ${d.x} ${midY}
                L ${d.x} ${d.y - nodeHeight/2}`;
    } else {
        const midX = (s.x + d.x) / 2;
        return `M ${s.x + nodeWidth/2} ${s.y}
                L ${midX} ${s.y}
                L ${midX} ${d.y}
                L ${d.x - nodeWidth/2} ${d.y}`;
    }
}

function toggle(d) {
    if (d.children) {
        d._children = d.children;
        d.children = null;
    } else {
        d.children = d._children;
        d._children = null;
        
        if (d.children) {
            d.children.forEach(child => {
                if (child.depth >= 2 && child.children) {
                    child._children = child.children;
                    child.children = null;
                }
            });
        }
    }
    update(d);
}

function expandAll() {
    root.each(d => {
        if (d._children) {
            d.children = d._children;
            d._children = null;
        }
    });
    update(root);
}

function collapseAll() {
    root.each(d => {
        if (d.depth >= 1 && d.children) {
            d._children = d.children;
            d.children = null;
        }
    });
    update(root);
}

function resetZoom() {
    const container = document.getElementById('orgChart');
    const width = container.clientWidth;
    
    svg.transition()
        .duration(750)
        .call(zoom.transform, d3.zoomIdentity.translate(width/2, 100));
}

function fitToScreen() {
    if (!root || !svg) return;
    
    const treeLayout = d3.tree().nodeSize([nodeWidth + 20, levelHeight]);
    const treeData = treeLayout(root);
    const nodes = treeData.descendants();
    
    if (nodes.length === 0) return;
    
    const minX = d3.min(nodes, d => d.x) - nodeWidth / 2;
    const maxX = d3.max(nodes, d => d.x) + nodeWidth / 2;
    const minY = d3.min(nodes, d => d.y) - nodeHeight / 2;
    const maxY = d3.max(nodes, d => d.y) + nodeHeight / 2;
    
    const width = maxX - minX;
    const height = maxY - minY;
    
    const container = document.getElementById('orgChart');
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    
    const scale = Math.min(
        (containerWidth * 0.9) / width,
        (containerHeight * 0.9) / height,
        1 
    );
    
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    
    svg.transition()
        .duration(750)
        .call(zoom.transform, 
            d3.zoomIdentity
                .translate(containerWidth / 2, containerHeight / 2)
                .scale(scale)
                .translate(-centerX, -centerY)
        );
}

function zoomIn() {
    svg.transition().call(zoom.scaleBy, 1.2);
}

function zoomOut() {
    svg.transition().call(zoom.scaleBy, 0.8);
}

function getBounds(printRoot) {
    const treeLayout = d3.tree().nodeSize([nodeWidth + 20, levelHeight]);
    const treeData = treeLayout(printRoot);
    const nodes = treeData.descendants();
    const minX = d3.min(nodes, d => d.x) - nodeWidth / 2 - 20;
    const maxX = d3.max(nodes, d => d.x) + nodeWidth / 2 + 20;
    const minY = d3.min(nodes, d => d.y) - nodeHeight / 2 - 20;
    const maxY = d3.max(nodes, d => d.y) + nodeHeight / 2 + 50;
    return { minX, maxX, minY, maxY };
}

function buildExpandedData(node) {
    const copy = {};
    Object.keys(node.data).forEach(key => {
        if (key !== 'children') {
            copy[key] = node.data[key];
        }
    });
    if (node.children) {
        copy.children = node.children.map(child => buildExpandedData(child));
    }
    copy.hasCollapsedChildren = !!(node._children && node._children.length);
    return copy;
}

function printChart() {
    const expandedData = buildExpandedData(root);
    const printRoot = d3.hierarchy(expandedData);
    const bounds = getBounds(printRoot);
    const viewWidth = bounds.maxX - bounds.minX;
    const viewHeight = bounds.maxY - bounds.minY;

    const orientation = appSettings.printOrientation || 'landscape';
    const size = appSettings.printSize || 'a4';
    
    let pageWidth, pageHeight;
    if (size === 'a4') {
        pageWidth = orientation === 'landscape' ? 1123 : 796;
        pageHeight = orientation === 'landscape' ? 796 : 1123;
    } else if (size === 'letter') {
        pageWidth = orientation === 'landscape' ? 1056 : 816;
        pageHeight = orientation === 'landscape' ? 816 : 1056;
    } else if (size === 'a3') {
        pageWidth = orientation === 'landscape' ? 1587 : 1123;
        pageHeight = orientation === 'landscape' ? 1123 : 1587;
    }

    let printWin = window.open('', '_blank');
    printWin.document.write(`<html><head><title>Org Chart Print</title>`);
    printWin.document.write(`<style>${document.querySelector('style').innerHTML}`);
    printWin.document.write(`@page { size: ${orientation}; margin: 0.5cm; }`);
    printWin.document.write(`body { margin: 0; padding: 0; }`);
    printWin.document.write(`</style></head><body>`);

    const printSvg = printWin.document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    printSvg.setAttribute('width', pageWidth);
    printSvg.setAttribute('height', pageHeight);
    printSvg.setAttribute('viewBox', `${bounds.minX} ${bounds.minY} ${viewWidth} ${viewHeight}`);
    printSvg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    const printG = printWin.document.createElementNS('http://www.w3.org/2000/svg', 'g');
    printSvg.appendChild(printG);
    printWin.document.body.appendChild(printSvg);

    const d3PrintG = d3.select(printG);

    const treeLayout = d3.tree().nodeSize([nodeWidth + 20, levelHeight]);
    const treeData = treeLayout(printRoot);
    const nodes = treeData.descendants();
    const links = treeData.links();

    d3PrintG.selectAll('.link')
        .data(links)
        .enter()
        .append('path')
        .attr('class', 'link')
        .attr('d', d => diagonal(d.source, d.target));

    const printNode = d3PrintG.selectAll('.node')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', 'node')
        .attr('transform', d => `translate(${d.x}, ${d.y})`);

    printNode.append('rect')
        .attr('class', 'node-rect')
        .attr('x', -nodeWidth/2)
        .attr('y', -nodeHeight/2)
        .attr('width', nodeWidth)
        .attr('height', nodeHeight)
        .style('fill', d => {
            const nodeColors = appSettings.nodeColors || {};
            switch(d.depth) {
                case 0: return nodeColors.level0 || '#90EE90';
                case 1: return nodeColors.level1 || '#FFFFE0';
                case 2: return nodeColors.level2 || '#E0F2FF';
                case 3: return nodeColors.level3 || '#FFE4E1';
                case 4: return nodeColors.level4 || '#E8DFF5';
                case 5: return nodeColors.level5 || '#FFEAA7';
                default: return '#F0F0F0'; 
            }
        })
        .style('stroke', d => {
            const nodeColors = appSettings.nodeColors || {};
            let fillColor;
            switch(d.depth) {
                case 0: fillColor = nodeColors.level0 || '#90EE90'; break;
                case 1: fillColor = nodeColors.level1 || '#FFFFE0'; break;
                case 2: fillColor = nodeColors.level2 || '#E0F2FF'; break;
                case 3: fillColor = nodeColors.level3 || '#FFE4E1'; break;
                case 4: fillColor = nodeColors.level4 || '#E8DFF5'; break;
                case 5: fillColor = nodeColors.level5 || '#FFEAA7'; break;
                default: fillColor = '#F0F0F0';
            }
            return adjustColor(fillColor, -50);
        })
        .style('stroke-width', '2px');

    if (appSettings.showProfileImages !== false) {
        printNode.append('image')
            .attr('xlink:href', userIconUrl)
            .attr('x', -nodeWidth/2 + 10)
            .attr('y', -nodeHeight/2 + (nodeHeight - 50) / 2)
            .attr('width', 50)
            .attr('height', 50)
            .attr('clip-path', 'circle(25px at 25px 25px)')
            .attr('preserveAspectRatio', 'xMidYMid slice');
    }

    printNode.append('text')
        .attr('class', 'node-text')
        .attr('x', appSettings.showProfileImages !== false ? nodeWidth/2 - 10 : 0)
        .attr('y', -20)
        .attr('text-anchor', appSettings.showProfileImages !== false ? 'end' : 'middle')
        .style('font-weight', 'bold')
        .text(d => {
            const name = d.data.name;
            return name.length > 22 ? name.substring(0, 22) + '...' : name;
        });

    printNode.append('text')
        .attr('class', 'node-title')
        .attr('x', appSettings.showProfileImages !== false ? nodeWidth/2 - 10 : 0)
        .attr('y', -5)
        .attr('text-anchor', appSettings.showProfileImages !== false ? 'end' : 'middle')
        .text(d => {
            const title = d.data.title;
            return title.length > 28 ? title.substring(0, 28) + '...' : title;
        });

    if (appSettings.showDepartments !== false) {
        printNode.append('text')
            .attr('class', 'node-department')
            .attr('x', appSettings.showProfileImages !== false ? nodeWidth/2 - 10 : 0)
            .attr('y', 25)
            .attr('text-anchor', appSettings.showProfileImages !== false ? 'end' : 'middle')
            .text(d => {
                const dept = d.data.department || 'Not specified';
                return dept.length > 28 ? dept.substring(0, 28) + '...' : dept;
            });
    }

    const printExpandBtn = printNode.append('g')
        .attr('class', 'expand-group')
        .style('display', d => (d.data.hasCollapsedChildren || (d.children && d.children.length)) ? 'block' : 'none');

    printExpandBtn.append('circle')
        .attr('class', 'expand-btn')
        .attr('cy', nodeHeight/2 + 10)
        .attr('r', 10);

    printExpandBtn.append('text')
        .attr('class', 'expand-text')
        .attr('y', nodeHeight/2 + 15)
        .attr('text-anchor', 'middle')
        .text(d => d.data.hasCollapsedChildren ? '+' : '-');

    printWin.document.write('</body></html>');
    printWin.document.close();
    printWin.focus();
    printWin.print();
}

function exportToImage(format = 'svg', exportFullChart = false) {
    const svgElement = createExportSVG(exportFullChart);
    const svgString = new XMLSerializer().serializeToString(svgElement);
    
    if (format === 'svg') {
        // Export as SVG
        const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(svgBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `org-chart-${new Date().toISOString().split('T')[0]}.svg`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } else if (format === 'png') {
        // Convert to PNG
        const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(svgBlob);
        const img = new Image();
        
        img.onload = function() {
            // Create high-res canvas (2x for better quality)
            const scale = 2;
            const canvas = document.createElement('canvas');
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;
            const ctx = canvas.getContext('2d');
            
            // White background
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Scale and draw
            ctx.scale(scale, scale);
            ctx.drawImage(img, 0, 0);
            
            // Download PNG
            canvas.toBlob(function(blob) {
                const pngUrl = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = pngUrl;
                a.download = `org-chart-${new Date().toISOString().split('T')[0]}.png`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(pngUrl);
            }, 'image/png');
            
            URL.revokeObjectURL(url);
        };
        
        img.src = url;
    }
}

function createExportSVG(exportFullChart = false) {
    let nodesToExport, linksToExport;
    
    if (exportFullChart) {
        // Original behavior - expand all and export everything
        const originalChildren = {};
        const saveAndExpand = (node) => {
            if (node._children) {
                originalChildren[node.data.id] = true;
                node.children = node._children;
                node._children = null;
            }
            if (node.children) {
                node.children.forEach(saveAndExpand);
            }
        };
        saveAndExpand(root);
        
        // Recalculate layout
        const treeLayout = d3.tree()
            .nodeSize(currentLayout === 'vertical' 
                ? [nodeWidth + 20, levelHeight] 
                : [levelHeight, nodeWidth + 20]);
        
        const treeData = treeLayout(root);
        nodesToExport = treeData.descendants();
        linksToExport = treeData.links();
        
        // Restore state after getting data
        const restoreState = (node) => {
            if (originalChildren[node.data.id]) {
                node._children = node.children;
                node.children = null;
            }
            if (node.children) {
                node.children.forEach(restoreState);
            }
        };
        restoreState(root);
        update(root);
    } else {
        // Export only visible nodes
        const treeLayout = d3.tree()
            .nodeSize(currentLayout === 'vertical' 
                ? [nodeWidth + 20, levelHeight] 
                : [levelHeight, nodeWidth + 20]);
        
        const treeData = treeLayout(root);
        nodesToExport = treeData.descendants();
        linksToExport = treeData.links();
    }
    
    // Swap for horizontal layout
    if (currentLayout === 'horizontal') {
        nodesToExport.forEach(d => {
            const temp = d.x;
            d.x = d.y;
            d.y = temp;
        });
    }
    
    // Calculate bounds
    const padding = 50;
    const minX = d3.min(nodesToExport, d => d.x) - nodeWidth/2 - padding;
    const maxX = d3.max(nodesToExport, d => d.x) + nodeWidth/2 + padding;
    const minY = d3.min(nodesToExport, d => d.y) - nodeHeight/2 - padding;
    const maxY = d3.max(nodesToExport, d => d.y) + nodeHeight/2 + padding;
    
    const width = maxX - minX;
    const height = maxY - minY;
    
    // Create SVG
    const exportSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    exportSvg.setAttribute('width', width);
    exportSvg.setAttribute('height', height);
    exportSvg.setAttribute('viewBox', `${minX} ${minY} ${width} ${height}`);
    exportSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    
    // White background
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('x', minX);
    bg.setAttribute('y', minY);
    bg.setAttribute('width', width);
    bg.setAttribute('height', height);
    bg.setAttribute('fill', 'white');
    exportSvg.appendChild(bg);
    
    // Add styles
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    style.textContent = `
        .link { fill: none; stroke: #999; stroke-width: 2px; }
        .node-rect { rx: 4; ry: 4; stroke-width: 2px; }
        .node-text { font-size: 14px; fill: #333; font-weight: 600; font-family: Arial, sans-serif; }
        .node-title { font-size: 11px; fill: #555; font-family: Arial, sans-serif; }
        .node-department { font-size: 11px; fill: #666; font-style: italic; font-family: Arial, sans-serif; }
        .expand-indicator { fill: #0078d4; font-size: 14px; font-weight: bold; }
    `;
    defs.appendChild(style);
    exportSvg.appendChild(defs);
    
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    
    // Draw links
    linksToExport.forEach(link => {
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('class', 'link');
        path.setAttribute('d', diagonal(link.source, link.target));
        g.appendChild(path);
    });
    
    // Draw nodes
    nodesToExport.forEach(d => {
        const nodeG = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        nodeG.setAttribute('transform', `translate(${d.x}, ${d.y})`);
        
        // Rectangle
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', -nodeWidth/2);
        rect.setAttribute('y', -nodeHeight/2);
        rect.setAttribute('width', nodeWidth);
        rect.setAttribute('height', nodeHeight);
        rect.setAttribute('rx', 4);
        rect.setAttribute('ry', 4);
        
        const nodeColors = appSettings.nodeColors || {};
        let fillColor;
        switch(d.depth) {
            case 0: fillColor = nodeColors.level0 || '#90EE90'; break;
            case 1: fillColor = nodeColors.level1 || '#FFFFE0'; break;
            case 2: fillColor = nodeColors.level2 || '#E0F2FF'; break;
            case 3: fillColor = nodeColors.level3 || '#FFE4E1'; break;
            case 4: fillColor = nodeColors.level4 || '#E8DFF5'; break;
            case 5: fillColor = nodeColors.level5 || '#FFEAA7'; break;
            default: fillColor = '#F0F0F0';
        }
        rect.setAttribute('fill', fillColor);
        rect.setAttribute('stroke', adjustColor(fillColor, -50));
        rect.setAttribute('stroke-width', '2');
        nodeG.appendChild(rect);
        
        // Name
        const nameText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        nameText.setAttribute('class', 'node-text');
        nameText.setAttribute('x', 0);
        nameText.setAttribute('y', -20);
        nameText.setAttribute('text-anchor', 'middle');
        nameText.textContent = d.data.name;
        nodeG.appendChild(nameText);
        
        // Title
        const titleText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        titleText.setAttribute('class', 'node-title');
        titleText.setAttribute('x', 0);
        titleText.setAttribute('y', -5);
        titleText.setAttribute('text-anchor', 'middle');
        titleText.textContent = d.data.title;
        nodeG.appendChild(titleText);
        
        // Department
        if (appSettings.showDepartments !== false && d.data.department) {
            const deptText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            deptText.setAttribute('class', 'node-department');
            deptText.setAttribute('x', 0);
            deptText.setAttribute('y', 25);
            deptText.setAttribute('text-anchor', 'middle');
            deptText.textContent = d.data.department;
            nodeG.appendChild(deptText);
        }
        
        // Add expand indicator if node has hidden children. Hiding this for the SVG export as it looks untidy. Remove comment markers from below if you want to add them back in for whatever reason.
        //if (d._children && d._children.length > 0) {
          //  const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            //circle.setAttribute('cx', 0);
            //circle.setAttribute('cy', currentLayout === 'vertical' ? nodeHeight/2 + 10 : 0);
            //circle.setAttribute('r', 10);
            //circle.setAttribute('fill', '#0078d4');
           // nodeG.appendChild(circle);
            
            //const plusText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            //plusText.setAttribute('class', 'expand-indicator');
            //plusText.setAttribute('x', 0);
            //plusText.setAttribute('y', currentLayout === 'vertical' ? nodeHeight/2 + 15 : 4);
            //plusText.setAttribute('text-anchor', 'middle');
            //plusText.setAttribute('fill', 'white');
            //plusText.textContent = '+';
            //nodeG.appendChild(plusText);
        //}
        
        g.appendChild(nodeG);
    });
    
    exportSvg.appendChild(g);
    return exportSvg;
}

function showEmployeeDetail(employee) {
    const detailPanel = document.getElementById('employeeDetail');
    const headerContent = document.getElementById('employeeDetailContent');
    const infoContent = document.getElementById('employeeInfo');
    
    const initials = employee.name.split(' ')
        .map(n => n[0])
        .join('')
        .substring(0, 2)
        .toUpperCase();
    
    headerContent.innerHTML = `
        <div class="employee-avatar">${initials}</div>
        <div class="employee-name">
            <h2>${employee.name}</h2>
        </div>
        <div class="employee-title">${employee.title}</div>
    `;
    
    let infoHTML = `
        <div class="info-item">
            <div class="info-label">Department</div>
            <div class="info-value">${employee.department || 'Not specified'}</div>
        </div>
        <div class="info-item">
            <div class="info-label">Email</div>
            <div class="info-value">
                ${employee.email ? `<a href="mailto:${employee.email}">${employee.email}</a>` : 'Not available'}
            </div>
        </div>
        <div class="info-item">
            <div class="info-label">Phone</div>
            <div class="info-value">${employee.phone || 'Not available'}</div>
        </div>
        <div class="info-item">
            <div class="info-label">Location</div>
            <div class="info-value">${employee.location || 'Not specified'}</div>
        </div>
    `;
    
    const directReports = employee.children || [];
    if (directReports.length > 0) {
        infoHTML += `
            <div class="direct-reports">
                <h3>Direct Reports (${directReports.length})</h3>
                ${directReports.map(report => `
                    <div class="report-item" onclick='showEmployeeDetail(${JSON.stringify(report).replace(/'/g, "\\'")})'>
                        <div class="report-name">${report.name}</div>
                        <div class="report-title">${report.title}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    infoContent.innerHTML = infoHTML;
    detailPanel.classList.add('active');
}

function closeEmployeeDetail() {
    document.getElementById('employeeDetail').classList.remove('active');
}

function findNodeById(node, targetId) {
    if (node.data.id === targetId) {
        return node;
    }
    if (node.children || node._children) {
        const children = node.children || node._children;
        for (let child of children) {
            const result = findNodeById(child, targetId);
            if (result) return result;
        }
    }
    return null;
}

function highlightNode(nodeId, highlight = true) {
    if (appSettings.searchHighlight !== false) {
        g.selectAll('.node-rect').each(function(d) {
            if (d.data.id === nodeId) {
                d3.select(this).classed('search-highlight', highlight);
            }
        });
    }
}

function clearHighlights() {
    g.selectAll('.node-rect').classed('search-highlight', false);
}

let searchTimeout;
const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');

searchInput.addEventListener('input', function(e) {
    clearTimeout(searchTimeout);
    const query = e.target.value.trim();
    
    clearHighlights();
    
    if (query.length < 2) {
        searchResults.classList.remove('active');
        return;
    }
    
    searchTimeout = setTimeout(() => {
        performSearch(query);
    }, 300);
});

searchInput.addEventListener('focus', function(e) {
    if (e.target.value.length >= 2) {
        performSearch(e.target.value);
    }
});

document.addEventListener('click', function(e) {
    if (!e.target.closest('.search-wrapper')) {
        searchResults.classList.remove('active');
    }
});

async function performSearch(query) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/search?q=${encodeURIComponent(query)}`);
        const results = await response.json();
        
        if (results.length > 0) {
            displaySearchResults(results);
        } else {
            searchResults.innerHTML = '<div class="search-result-item">No results found</div>';
            searchResults.classList.add('active');
        }
    } catch (error) {
        console.error('Search error:', error);
    }
}

function displaySearchResults(results) {
    searchResults.innerHTML = results.map(emp => `
        <div class="search-result-item" onclick="selectSearchResult('${emp.id}')">
            <div class="search-result-name">${emp.name}</div>
            <div class="search-result-title">${emp.title}</div>
        </div>
    `).join('');
    searchResults.classList.add('active');
}

function selectSearchResult(employeeId) {
    const employee = allEmployees.find(emp => emp.id === employeeId);
    if (employee) {
        showEmployeeDetail(employee);
        searchResults.classList.remove('active');
        searchInput.value = '';
        
        expandToEmployee(employeeId);
    }
}

function expandToEmployee(employeeId) {
    if (appSettings.searchAutoExpand === false) {
        const targetNode = findNodeById(root, employeeId);
        if (targetNode) {
            highlightNode(employeeId);
            showEmployeeDetail(targetNode.data);
        }
        return;
    }
    
    const path = [];
    
    function findPath(node, targetId, currentPath) {
        currentPath.push(node);
        
        if (node.data.id === targetId) {
            path.push(...currentPath);
            return true;
        }
        
        if (node.children || node._children) {
            const children = node.children || node._children;
            for (let child of children) {
                if (findPath(child, targetId, [...currentPath])) {
                    return true;
                }
            }
        }
        
        return false;
    }
    
    findPath(root, employeeId, []);
    
    path.forEach(node => {
        if (node._children) {
            node.children = node._children;
            node._children = null;
        }
    });
    
    update(root);
    
    const targetNode = path[path.length - 1];
    if (targetNode) {
        setTimeout(() => {
            highlightNode(employeeId);
        }, 600);
        
        const container = document.getElementById('orgChart');
        const width = container.clientWidth;
        const height = container.clientHeight;
        
        svg.transition()
            .duration(750)
            .call(zoom.transform, 
                d3.zoomIdentity
                    .translate(width/2, height/2)
                    .scale(1)
                    .translate(-targetNode.x, -targetNode.y)
            );
    }
}

document.addEventListener('DOMContentLoaded', init);

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeEmployeeDetail();
        clearHighlights();
    }
});