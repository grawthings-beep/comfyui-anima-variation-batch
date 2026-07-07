import { app } from "../../scripts/app.js";

const PREVIEW_WIDGET_NAME = "pose_preview";
const PREVIEW_HEIGHT = 260;

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

const BASE_POINTS = {
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
  left_hip: [-0.24, 0.0, 0.02],
  right_hip: [0.24, 0.0, 0.02],
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

function radians(value) {
  return (value * Math.PI) / 180;
}

function copyPoint(point) {
  return [point[0], point[1], point[2]];
}

function armPoints(side, shoulder, armRaise, elbowBend) {
  const raise = radians(clamp(Number(armRaise), -90, 160));
  const bend = clamp(Number(elbowBend), -80, 150);
  const upperLen = 0.51;
  const lowerLen = 0.49;
  const elbow = [
    shoulder[0] + side * Math.sin(raise) * upperLen * 0.92,
    shoulder[1] - Math.cos(raise) * upperLen,
    shoulder[2] - 0.04,
  ];

  const lower = radians(clamp(Number(armRaise), -90, 160) - bend);
  const wrist = [
    elbow[0] + side * Math.sin(lower) * lowerLen * 0.92,
    elbow[1] - Math.cos(lower) * lowerLen,
    elbow[2] - 0.04,
  ];
  return [elbow, wrist];
}

function legPoints(side, hip, legLift, kneeBend) {
  const lift = clamp(Number(legLift), -45, 90);
  const bend = clamp(Number(kneeBend), -40, 120);
  const upper = radians(lift);
  const upperLen = 0.66;
  const lowerLen = 0.57;
  const knee = [
    hip[0] + side * 0.02,
    hip[1] - Math.cos(upper) * upperLen,
    hip[2] - Math.sin(upper) * upperLen * 0.85 + 0.03,
  ];

  const lower = radians(lift - bend);
  const ankle = [
    knee[0] + side * 0.02,
    knee[1] - Math.cos(lower) * lowerLen,
    knee[2] - Math.sin(lower) * lowerLen * 0.85 - 0.07,
  ];
  return [knee, ankle];
}

function buildPoints(node) {
  const points = Object.fromEntries(
    Object.entries(BASE_POINTS).map(([name, point]) => [name, copyPoint(point)]),
  );

  [points.left_elbow, points.left_wrist] = armPoints(
    -1,
    points.left_shoulder,
    widgetValue(node, "left_arm_raise", 15),
    widgetValue(node, "left_elbow_bend", 25),
  );
  [points.right_elbow, points.right_wrist] = armPoints(
    1,
    points.right_shoulder,
    widgetValue(node, "right_arm_raise", 15),
    widgetValue(node, "right_elbow_bend", 25),
  );
  [points.left_knee, points.left_ankle] = legPoints(
    -1,
    points.left_hip,
    widgetValue(node, "left_leg_lift", 0),
    widgetValue(node, "left_knee_bend", 0),
  );
  [points.right_knee, points.right_ankle] = legPoints(
    1,
    points.right_hip,
    widgetValue(node, "right_leg_lift", 0),
    widgetValue(node, "right_knee_bend", 0),
  );
  return points;
}

function rotate(point, yaw, pitch) {
  const [x, y, z] = point;
  const yawRad = radians(yaw);
  const pitchRad = radians(pitch);
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
  const rollRad = radians(roll);
  const cosRoll = Math.cos(rollRad);
  const sinRoll = Math.sin(rollRad);
  return {
    x: box.x + box.width * 0.5 + px * cosRoll - py * sinRoll,
    y: box.y + box.height * 0.56 - (px * sinRoll + py * cosRoll),
    z,
  };
}

function drawRoundRect(ctx, x, y, width, height, radius) {
  if (ctx.roundRect) {
    ctx.roundRect(x, y, width, height, radius);
    return;
  }
  const r = Math.min(radius, width * 0.5, height * 0.5);
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + width - r, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + r);
  ctx.lineTo(x + width, y + height - r);
  ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  ctx.lineTo(x + r, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
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

function drawPose(ctx, node, box) {
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
  drawRoundRect(ctx, box.x, box.y, box.width, box.height, 8);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = "#aaa";
  ctx.font = "12px sans-serif";
  ctx.fillText(`live OpenPose preview  yaw ${Math.round(yaw)} deg`, box.x + 10, box.y + 18);

  const poseBox = {
    x: box.x + 12,
    y: box.y + 24,
    width: box.width - 24,
    height: box.height - 34,
  };
  const sourcePoints = buildPoints(node);
  const points = {};
  for (const [name, point] of Object.entries(sourcePoints)) {
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

  const frontVisibility = Math.cos(radians(yaw));
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

function addPreviewWidget(node) {
  if (node.widgets?.some((widget) => widget.name === PREVIEW_WIDGET_NAME)) {
    return;
  }

  const previewWidget = {
    name: PREVIEW_WIDGET_NAME,
    type: "anima_360_preview",
    serialize: false,
    computeSize(width) {
      return [width, PREVIEW_HEIGHT];
    },
    draw(ctx, drawNode, widgetWidth, y, widgetHeight = PREVIEW_HEIGHT) {
      drawPose(ctx, drawNode, {
        x: 14,
        y: y + 4,
        width: Math.max(220, widgetWidth - 28),
        height: Math.max(180, widgetHeight - 8),
      });
    },
  };

  node.widgets = node.widgets || [];
  node.widgets.unshift(previewWidget);
}

function wrapWidgetCallbacks(node) {
  for (const widget of node.widgets ?? []) {
    if (widget.name === PREVIEW_WIDGET_NAME || widget._animaPreviewWrapped) {
      continue;
    }
    const originalCallback = widget.callback;
    widget.callback = (...args) => {
      const callbackResult = originalCallback?.apply(widget, args);
      markDirty(node);
      return callbackResult;
    };
    widget._animaPreviewWrapped = true;
  }
}

app.registerExtension({
  name: "grawthings.anima.360.preview",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    const comfyClass = nodeType.comfyClass ?? nodeType.ComfyClass ?? nodeData?.name;
    if (comfyClass !== "Anima360AngleControl") return;

    const originalCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = originalCreated?.apply(this, arguments);
      addPreviewWidget(this);
      wrapWidgetCallbacks(this);
      this.size = [
        Math.max(this.size?.[0] ?? 640, 680),
        Math.max(this.size?.[1] ?? 820, 900),
      ];
      markDirty(this);
      return result;
    };
  },
});
