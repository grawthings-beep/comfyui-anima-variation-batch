import { app } from "../../scripts/app.js";

const SEGMENTS = [
  ["neck", "right_shoulder", "#ff0000"],
  ["right_shoulder", "right_elbow", "#ff5500"],
  ["right_elbow", "right_wrist", "#ffaa00"],
  ["neck", "left_shoulder", "#ffff00"],
  ["left_shoulder", "left_elbow", "#aaff00"],
  ["left_elbow", "left_wrist", "#55ff00"],
  ["neck", "pelvis", "#00ff00"],
  ["pelvis", "right_hip", "#00ff55"],
  ["right_hip", "right_knee", "#00ffaa"],
  ["right_knee", "right_ankle", "#00ffff"],
  ["pelvis", "left_hip", "#00aaff"],
  ["left_hip", "left_knee", "#0055ff"],
  ["left_knee", "left_ankle", "#0000ff"],
  ["neck", "head", "#5500ff"],
  ["head", "nose", "#aa00ff"],
  ["head", "left_eye", "#ff00ff"],
  ["head", "right_eye", "#ff00aa"],
  ["chest_front", "pelvis_front", "#ffffff"],
  ["chest_back", "pelvis_back", "#a0a0ff"],
  ["chest_front", "chest_back", "#ffffff"],
  ["pelvis_front", "pelvis_back", "#a0a0ff"],
];

const JOINTS = [
  "head",
  "neck",
  "pelvis",
  "left_shoulder",
  "right_shoulder",
  "left_elbow",
  "right_elbow",
  "left_wrist",
  "right_wrist",
  "left_hip",
  "right_hip",
  "left_knee",
  "right_knee",
  "left_ankle",
  "right_ankle",
  "nose",
];

const POINTS = {
  head: [0.0, 1.33, -0.02],
  neck: [0.0, 1.05, 0.0],
  chest: [0.0, 0.72, -0.02],
  pelvis: [0.0, 0.0, 0.02],
  chest_front: [0.0, 0.74, -0.16],
  chest_back: [0.0, 0.74, 0.16],
  pelvis_front: [0.0, 0.02, -0.12],
  pelvis_back: [0.0, 0.02, 0.12],
  left_shoulder: [-0.38, 0.94, 0.0],
  right_shoulder: [0.38, 0.94, 0.0],
  left_elbow: [-0.52, 0.45, -0.04],
  right_elbow: [0.52, 0.45, -0.04],
  left_wrist: [-0.43, -0.03, -0.08],
  right_wrist: [0.43, -0.03, -0.08],
  left_hip: [-0.24, 0.0, 0.02],
  right_hip: [0.24, 0.0, 0.02],
  left_knee: [-0.22, -0.66, 0.05],
  right_knee: [0.22, -0.66, 0.05],
  left_ankle: [-0.24, -1.22, -0.02],
  right_ankle: [0.24, -1.22, -0.02],
  nose: [0.0, 1.33, -0.28],
  left_eye: [-0.07, 1.38, -0.22],
  right_eye: [0.07, 1.38, -0.22],
  mouth_left: [-0.06, 1.27, -0.22],
  mouth_right: [0.06, 1.27, -0.22],
};

function widgetValue(node, name, fallback) {
  const widget = node.widgets?.find((item) => item.name === name);
  return widget ? widget.value : fallback;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function rotate(point, yaw, pitch) {
  const [x, y, z] = point;
  const yawRad = (yaw * Math.PI) / 180;
  const pitchRad = (pitch * Math.PI) / 180;
  const cosYaw = Math.cos(yawRad);
  const sinYaw = Math.sin(yawRad);
  const xr = x * cosYaw + z * sinYaw;
  const zr = -x * sinYaw + z * cosYaw;
  const cosPitch = Math.cos(pitchRad);
  const sinPitch = Math.sin(pitchRad);
  return [xr, y * cosPitch - zr * sinPitch, y * sinPitch + zr * cosPitch];
}

function project(point, box, yaw, pitch, roll, zoom) {
  const [x, y, z] = rotate(point, yaw, pitch);
  const denom = Math.max(0.8, 3.2 + z);
  const scale = Math.min(box.width, box.height) * (0.95 + zoom * 0.07);
  const px = (x * scale) / denom;
  const py = (y * scale) / denom;
  const rollRad = (roll * Math.PI) / 180;
  const cosRoll = Math.cos(rollRad);
  const sinRoll = Math.sin(rollRad);
  return {
    x: box.x + box.width * 0.5 + px * cosRoll - py * sinRoll,
    y: box.y + box.height * 0.56 - (px * sinRoll + py * cosRoll),
    z,
  };
}

function drawSegment(ctx, points, start, end, color, width) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(points[start].x, points[start].y);
  ctx.lineTo(points[end].x, points[end].y);
  ctx.stroke();
}

function drawPose(ctx, node) {
  const padding = 14;
  const box = {
    x: padding,
    y: Math.max(320, node.size[1] - 250),
    width: Math.max(220, node.size[0] - padding * 2),
    height: 230,
  };
  const yaw = Number(widgetValue(node, "yaw_degrees", 45)) % 360;
  const pitch = clamp(Number(widgetValue(node, "pitch_degrees", 0)), -75, 75);
  const roll = clamp(Number(widgetValue(node, "roll_degrees", 0)), -45, 45);
  const zoom = clamp(Number(widgetValue(node, "zoom", 5)), 0, 10);
  const thickness = clamp(Number(widgetValue(node, "line_thickness", 6)), 1, 24);

  ctx.save();
  ctx.fillStyle = "#060606";
  ctx.strokeStyle = "#333";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(box.x, box.y, box.width, box.height, 8);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = "#aaa";
  ctx.font = "12px sans-serif";
  ctx.fillText(`live OpenPose preview  yaw ${Math.round(yaw)}°`, box.x + 10, box.y + 18);

  const poseBox = {
    x: box.x + 12,
    y: box.y + 24,
    width: box.width - 24,
    height: box.height - 34,
  };
  const points = {};
  for (const [name, point] of Object.entries(POINTS)) {
    points[name] = project(point, poseBox, yaw, pitch, roll, zoom);
  }

  for (const segment of [...SEGMENTS].sort((a, b) => {
    const za = (points[a[0]].z + points[a[1]].z) * 0.5;
    const zb = (points[b[0]].z + points[b[1]].z) * 0.5;
    return zb - za;
  })) {
    drawSegment(ctx, points, segment[0], segment[1], segment[2], Math.max(2, thickness * 0.65));
  }

  const head = points.head;
  const radius = Math.max(11, thickness * 2.2);
  ctx.strokeStyle = "#5500ff";
  ctx.lineWidth = Math.max(2, thickness * 0.45);
  ctx.beginPath();
  ctx.ellipse(head.x, head.y, radius, radius * 1.12, 0, 0, Math.PI * 2);
  ctx.stroke();

  const frontVisibility = Math.cos((yaw * Math.PI) / 180);
  if (frontVisibility > 0.18) {
    drawSegment(ctx, points, "mouth_left", "mouth_right", "#ffffff", Math.max(1, thickness * 0.4));
  } else if (frontVisibility < -0.18) {
    ctx.strokeStyle = "#a0a0ff";
    ctx.lineWidth = Math.max(1, thickness * 0.35);
    ctx.beginPath();
    ctx.moveTo(head.x, head.y - radius);
    ctx.lineTo(head.x, head.y + radius);
    ctx.stroke();
  }

  ctx.fillStyle = "#ffffff";
  for (const name of JOINTS) {
    const point = points[name];
    const jointRadius = Math.max(2, thickness * 0.35);
    ctx.beginPath();
    ctx.arc(point.x, point.y, jointRadius, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function markDirty(node) {
  node.setDirtyCanvas?.(true, true);
  app.graph?.setDirtyCanvas?.(true, true);
}

app.registerExtension({
  name: "grawthings.anima.360.preview",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    const comfyClass = nodeType.comfyClass ?? nodeType.ComfyClass ?? nodeData?.name;
    if (comfyClass !== "Anima360AngleControl") return;

    const originalCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = originalCreated?.apply(this, arguments);
      this.size = [Math.max(this.size?.[0] ?? 560, 620), Math.max(this.size?.[1] ?? 430, 590)];
      for (const widget of this.widgets ?? []) {
        const originalCallback = widget.callback;
        widget.callback = (...args) => {
          const callbackResult = originalCallback?.apply(widget, args);
          markDirty(this);
          return callbackResult;
        };
      }
      markDirty(this);
      return result;
    };

    const originalDrawForeground = nodeType.prototype.onDrawForeground;
    nodeType.prototype.onDrawForeground = function (ctx) {
      originalDrawForeground?.apply(this, arguments);
      if (!this.flags?.collapsed) {
        drawPose(ctx, this);
      }
    };
  },
});
