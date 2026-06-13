/**
 * Fabric.js Canvas Logic for Auto Image Occlusion
 */

let canvas;
let bridge;
let currentTool = 'select';
let isMouseDown = false;
let origX = 0;
let origY = 0;
let activeObject = null;

let originalWidth = 0;
let originalHeight = 0;
let zoomLevel = 1;

// Initialize WebChannel
new QWebChannel(qt.webChannelTransport, function (channel) {
    bridge = channel.objects.bridge;
    console.log("QWebChannel initialized");
});

function initCanvas(viewportWidth, viewportHeight) {
    canvas = new fabric.Canvas('c', {
        width: viewportWidth,
        height: viewportHeight,
        preserveObjectStacking: true
    });

    // Handle object selection
    canvas.on('selection:created', (e) => {
        if (bridge) bridge.onSelectionChanged(true);
    });
    canvas.on('selection:cleared', (e) => {
        if (bridge) bridge.onSelectionChanged(false);
    });
    
    // Auto-update bridge when objects are modified
    canvas.on('object:modified', () => console.log('Object modified'));

    // Handle path creation for lasso tool
    canvas.on('path:created', function(e) {
        const path = e.path;
        path.set({
            fill: '#fffcc4',
            stroke: '#000',
            strokeWidth: 1.5,
            opacity: 0.8,
            shape_type: 'path'
        });
        if (bridge) bridge.onBoxAdded();
    });

    // Ensure new objects follow the current tool's selectability rules
    canvas.on('object:added', function(e) {
        const obj = e.target;
        if (obj === canvas.backgroundImage) return;
        
        if (obj.type === 'path' && !obj.shape_type) {
            obj.set('shape_type', 'path');
        }

        const isSelectMode = (currentTool === 'select');
        obj.selectable = isSelectMode;
        obj.evented = isSelectMode;
    });

    // Mouse events for shape drawing (Rectangle & Ellipse)
    canvas.on('mouse:down', function(o) {
        if (currentTool !== 'rect' && currentTool !== 'ellipse') return;
        
        isMouseDown = true;
        const pointer = canvas.getPointer(o.e);
        origX = pointer.x;
        origY = pointer.y;
        
        if (currentTool === 'rect') {
            activeObject = new fabric.Rect({
                left: origX,
                top: origY,
                width: 0,
                height: 0,
                fill: '#fffcc4',
                stroke: '#000',
                strokeWidth: 1.5,
                opacity: 0.8,
                transparentCorners: false,
                cornerSize: 8,
                cornerColor: '#3b82f6',
                shape_type: 'rect'
            });
        } else if (currentTool === 'ellipse') {
            activeObject = new fabric.Ellipse({
                left: origX,
                top: origY,
                rx: 0,
                ry: 0,
                fill: '#fffcc4',
                stroke: '#000',
                strokeWidth: 1.5,
                opacity: 0.8,
                transparentCorners: false,
                cornerSize: 8,
                cornerColor: '#3b82f6',
                shape_type: 'ellipse'
            });
        }
        
        canvas.add(activeObject);
    });

    canvas.on('mouse:move', function(o) {
        if (!isMouseDown || !activeObject) return;
        
        const pointer = canvas.getPointer(o.e);
        
        if (currentTool === 'rect') {
            const left = Math.min(origX, pointer.x);
            const top = Math.min(origY, pointer.y);
            const width = Math.abs(origX - pointer.x);
            const height = Math.abs(origY - pointer.y);
            
            activeObject.set({ left: left, top: top, width: width, height: height });
        } else if (currentTool === 'ellipse') {
            const left = Math.min(origX, pointer.x);
            const top = Math.min(origY, pointer.y);
            const rx = Math.abs(origX - pointer.x) / 2;
            const ry = Math.abs(origY - pointer.y) / 2;
            
            activeObject.set({ left: left, top: top, rx: rx, ry: ry });
        }
        
        canvas.renderAll();
    });

    canvas.on('mouse:up', function() {
        if (!isMouseDown) return;
        isMouseDown = false;
        
        if (activeObject) {
            const width = activeObject.width || (activeObject.rx * 2) || 0;
            const height = activeObject.height || (activeObject.ry * 2) || 0;
            
            // Remove shapes that are too small
            if (width < 5 || height < 5) {
                canvas.remove(activeObject);
            } else {
                if (bridge) bridge.onBoxAdded();
            }
            activeObject = null;
        }
    });
}

/**
 * Update canvas zoom and scale
 */
function updateCanvasScale() {
    if (!canvas || originalWidth === 0) return;
    
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    canvas.setDimensions({ width: viewportWidth, height: viewportHeight });
    
    const scaleX = viewportWidth / originalWidth;
    const scaleY = viewportHeight / originalHeight;
    zoomLevel = Math.min(scaleX, scaleY, 1); // Limit zoom to 100% maximum
    
    canvas.setZoom(zoomLevel);
    canvas.requestRenderAll();
}

window.addEventListener('resize', updateCanvasScale);

/**
 * Loads an image as background
 * @param {string} base64Data 
 */
function loadImage(base64Data, width, height) {
    originalWidth = width;
    originalHeight = height;
    
    const viewportWidth = window.innerWidth || 800;
    const viewportHeight = window.innerHeight || 600;

    if (!canvas) {
        initCanvas(viewportWidth, viewportHeight);
    } else {
        canvas.clear();
    }
    
    updateCanvasScale();

    fabric.Image.fromURL(base64Data, function(img) {
        canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
            originX: 'left',
            originY: 'top',
            left: 0,
            top: 0
        });
    });
}

/**
 * Adds a rectangle mask (typically from OCR)
 */
function addRect(x, y, w, h, text = "") {
    const rect = new fabric.Rect({
        left: x,
        top: y,
        width: w,
        height: h,
        fill: '#fffcc4',
        stroke: '#000',
        strokeWidth: 1.5,
        opacity: 0.8,
        transparentCorners: false,
        cornerSize: 8,
        cornerColor: '#3b82f6',
        shape_type: 'rect'
    });
    
    rect.set('data', { text: text });
    canvas.add(rect);
    canvas.renderAll();
}

/**
 * Tool Switching
 */
function setTool(tool) {
    currentTool = tool;
    canvas.isDrawingMode = (tool === 'lasso');
    
    if (canvas.isDrawingMode) {
        canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
        canvas.freeDrawingBrush.width = 3;
        canvas.freeDrawingBrush.color = '#fffcc4';
    }
    
    const isSelectMode = (tool === 'select');
    canvas.selection = isSelectMode;
    canvas.forEachObject(function(o) {
        if (o === canvas.backgroundImage) return;
        o.selectable = isSelectMode;
        o.evented = isSelectMode;
    });
}

/**
 * Grouping
 */
function groupSelected() {
    if (!canvas.getActiveObject()) return;
    if (canvas.getActiveObject().type !== 'activeSelection') return;
    
    canvas.getActiveObject().toGroup();
    canvas.requestRenderAll();
}

function ungroupSelected() {
    const activeObject = canvas.getActiveObject();
    if (!activeObject || activeObject.type !== 'group') return;
    
    activeObject.toActiveSelection();
    canvas.requestRenderAll();
}

/**
 * Deletes selected shapes
 */
function deleteSelected() {
    const activeObjects = canvas.getActiveObjects();
    if (activeObjects.length > 0) {
        activeObjects.forEach((obj) => {
            canvas.remove(obj);
        });
        canvas.discardActiveObject();
        canvas.requestRenderAll();
    }
}

/**
 * Export SVG
 */
function getSVGData() {
    return canvas.toSVG();
}

/**
 * Gets JSON data for exporting mask objects to Python
 */
function getExportData() {
    if (!canvas) return JSON.stringify({ width: 0, height: 0, objects: [] });
    const objects = canvas.toObject(['shape_type', 'data']).objects;
    return JSON.stringify({
        width: canvas.width,
        height: canvas.height,
        objects: objects
    });
}

/**
 * Generates OM, Q, and A SVGs for all masks based on the selected mode.
 * Returns a JSON string containing all generated SVG documents.
 */
function generateAllSVGs(mode) {
    const masks = canvas.getObjects().filter(o => o !== canvas.backgroundImage);
    
    // Save original states
    const originalStates = masks.map(m => {
        if (m.type === 'group') {
            return {
                visible: m.get('visible'),
                children: m.getObjects().map(c => ({
                    fill: c.get('fill'),
                    opacity: c.get('opacity')
                }))
            };
        } else {
            return {
                fill: m.get('fill'),
                visible: m.get('visible'),
                opacity: m.get('opacity')
            };
        }
    });

    function setEntityProperties(m, props) {
        if (m.type === 'group') {
            if (props.visible !== undefined) m.set({ visible: props.visible });
            m.getObjects().forEach(c => {
                c.set({
                    fill: props.fill !== undefined ? props.fill : c.get('fill'),
                    opacity: props.opacity !== undefined ? props.opacity : c.get('opacity')
                });
            });
        } else {
            m.set(props);
        }
    }

    // 1. Generate OM (Original Mask - all yellow, visible)
    masks.forEach(m => {
        setEntityProperties(m, { fill: '#fffcc4', visible: true, opacity: 0.8 });
    });
    canvas.discardActiveObject();
    canvas.renderAll();
    const om_svg = canvas.toSVG();

    const q_svgs = [];
    const a_svgs = [];

    // 2. Generate Q and A SVGs for each mask
    for (let i = 0; i < masks.length; i++) {
        // Question
        masks.forEach((m, idx) => {
            if (idx === i) {
                setEntityProperties(m, { fill: '#fc4242', visible: true, opacity: 0.8 });
            } else {
                if (mode === "Hide One, Reveal One") {
                    setEntityProperties(m, { visible: false });
                } else {
                    setEntityProperties(m, { fill: '#fffcc4', visible: true, opacity: 0.8 });
                }
            }
        });
        canvas.renderAll();
        q_svgs.push(canvas.toSVG());

        // Answer
        masks.forEach((m, idx) => {
            if (idx === i) {
                setEntityProperties(m, { visible: false });
            } else {
                if (mode === "Hide One, Reveal One" || mode === "Hide All, Reveal All") {
                    setEntityProperties(m, { visible: false });
                } else {
                    setEntityProperties(m, { fill: '#fffcc4', visible: true, opacity: 0.8 });
                }
            }
        });
        canvas.renderAll();
        a_svgs.push(canvas.toSVG());
    }

    // Restore original states
    masks.forEach((m, idx) => {
        const orig = originalStates[idx];
        if (m.type === 'group') {
            m.set({ visible: orig.visible });
            m.getObjects().forEach((c, cIdx) => {
                c.set(orig.children[cIdx]);
            });
        } else {
            m.set(orig);
        }
    });
    canvas.renderAll();

    return JSON.stringify({
        om_svg: om_svg,
        q_svgs: q_svgs,
        a_svgs: a_svgs
    });
}
