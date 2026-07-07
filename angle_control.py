# SPDX-License-Identifier: GPL-3.0-only

import math

from PIL import Image, ImageDraw


OPENPOSE_SEGMENTS = (
    ("neck", "right_shoulder", (255, 0, 0)),
    ("right_shoulder", "right_elbow", (255, 85, 0)),
    ("right_elbow", "right_wrist", (255, 170, 0)),
    ("neck", "left_shoulder", (255, 255, 0)),
    ("left_shoulder", "left_elbow", (170, 255, 0)),
    ("left_elbow", "left_wrist", (85, 255, 0)),
    ("neck", "pelvis", (0, 255, 0)),
    ("pelvis", "right_hip", (0, 255, 85)),
    ("right_hip", "right_knee", (0, 255, 170)),
    ("right_knee", "right_ankle", (0, 255, 255)),
    ("pelvis", "left_hip", (0, 170, 255)),
    ("left_hip", "left_knee", (0, 85, 255)),
    ("left_knee", "left_ankle", (0, 0, 255)),
    ("neck", "head", (85, 0, 255)),
    ("head", "nose", (170, 0, 255)),
    ("head", "left_eye", (255, 0, 255)),
    ("head", "right_eye", (255, 0, 170)),
    ("chest_front", "pelvis_front", (255, 255, 255)),
    ("chest_back", "pelvis_back", (160, 160, 255)),
    ("chest_front", "chest_back", (255, 255, 255)),
    ("pelvis_front", "pelvis_back", (160, 160, 255)),
)

OPENPOSE_JOINTS = (
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
)

DEFAULT_LEFT_ARM_RAISE = 15
DEFAULT_RIGHT_ARM_RAISE = 15
DEFAULT_LEFT_ELBOW_BEND = 25
DEFAULT_RIGHT_ELBOW_BEND = 25
DEFAULT_LEFT_LEG_LIFT = 0
DEFAULT_RIGHT_LEG_LIFT = 0
DEFAULT_LEFT_KNEE_BEND = 0
DEFAULT_RIGHT_KNEE_BEND = 0


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def normalize_yaw(yaw_degrees):
    return float(yaw_degrees) % 360.0


def describe_yaw(yaw_degrees):
    yaw = normalize_yaw(yaw_degrees)
    sectors = (
        (22.5, "front view"),
        (67.5, "front-right three-quarter view"),
        (112.5, "right profile view"),
        (157.5, "back-right three-quarter view"),
        (202.5, "back view"),
        (247.5, "back-left three-quarter view"),
        (292.5, "left profile view"),
        (337.5, "front-left three-quarter view"),
        (360.0, "front view"),
    )
    for limit, label in sectors:
        if yaw < limit:
            return label
    return "front view"


def describe_pitch(pitch_degrees):
    pitch = float(pitch_degrees)
    if pitch <= -60:
        return "extreme low-angle worm's-eye view"
    if pitch <= -30:
        return "low-angle view"
    if pitch < 20:
        return "eye-level view"
    if pitch < 50:
        return "high-angle view"
    return "top-down bird's-eye view"


def describe_zoom(zoom):
    zoom = float(zoom)
    if zoom < 2:
        return "extreme wide shot"
    if zoom < 4:
        return "wide shot"
    if zoom < 6:
        return "full body shot"
    if zoom < 8:
        return "cowboy shot"
    return "upper body close-up"


def build_angle_prompt(yaw_degrees, pitch_degrees, zoom):
    yaw = normalize_yaw(yaw_degrees)
    return (
        f"{describe_yaw(yaw)}, {describe_pitch(pitch_degrees)}, "
        f"{describe_zoom(zoom)}, camera yaw {yaw:.0f} degrees, "
        "match the OpenPose control reference perspective"
    )


def build_pose_prompt(
    left_arm_raise=DEFAULT_LEFT_ARM_RAISE,
    right_arm_raise=DEFAULT_RIGHT_ARM_RAISE,
    left_elbow_bend=DEFAULT_LEFT_ELBOW_BEND,
    right_elbow_bend=DEFAULT_RIGHT_ELBOW_BEND,
    left_leg_lift=DEFAULT_LEFT_LEG_LIFT,
    right_leg_lift=DEFAULT_RIGHT_LEG_LIFT,
    left_knee_bend=DEFAULT_LEFT_KNEE_BEND,
    right_knee_bend=DEFAULT_RIGHT_KNEE_BEND,
):
    terms = []

    def add_arm(side, raise_value, bend_value):
        raise_value = float(raise_value)
        bend_value = float(bend_value)
        if raise_value >= 70:
            terms.append(f"{side} arm raised")
        elif raise_value <= -20:
            terms.append(f"{side} arm lowered")
        if bend_value >= 55:
            terms.append(f"{side} elbow bent")
        elif bend_value <= -20:
            terms.append(f"{side} arm extended")

    def add_leg(side, lift_value, bend_value):
        lift_value = float(lift_value)
        bend_value = float(bend_value)
        if lift_value >= 35:
            terms.append(f"{side} knee lifted forward")
        elif lift_value <= -20:
            terms.append(f"{side} leg stretched back")
        if bend_value >= 40:
            terms.append(f"{side} knee bent")
        elif bend_value <= -20:
            terms.append(f"{side} leg straight")

    add_arm("left", left_arm_raise, left_elbow_bend)
    add_arm("right", right_arm_raise, right_elbow_bend)
    add_leg("left", left_leg_lift, left_knee_bend)
    add_leg("right", right_leg_lift, right_knee_bend)
    return ", ".join(terms)


def join_prompt(*parts):
    return ", ".join(
        str(part).strip(" \t\r\n,")
        for part in parts
        if str(part).strip(" \t\r\n,")
    )


def build_full_prompt(
    base_prompt,
    yaw_degrees,
    pitch_degrees,
    zoom,
    add_angle_prompt,
    left_arm_raise=DEFAULT_LEFT_ARM_RAISE,
    right_arm_raise=DEFAULT_RIGHT_ARM_RAISE,
    left_elbow_bend=DEFAULT_LEFT_ELBOW_BEND,
    right_elbow_bend=DEFAULT_RIGHT_ELBOW_BEND,
    left_leg_lift=DEFAULT_LEFT_LEG_LIFT,
    right_leg_lift=DEFAULT_RIGHT_LEG_LIFT,
    left_knee_bend=DEFAULT_LEFT_KNEE_BEND,
    right_knee_bend=DEFAULT_RIGHT_KNEE_BEND,
):
    if not add_angle_prompt:
        return str(base_prompt).strip()
    return join_prompt(
        base_prompt,
        build_angle_prompt(yaw_degrees, pitch_degrees, zoom),
        build_pose_prompt(
            left_arm_raise,
            right_arm_raise,
            left_elbow_bend,
            right_elbow_bend,
            left_leg_lift,
            right_leg_lift,
            left_knee_bend,
            right_knee_bend,
        ),
    )


def _rotate(point, yaw, pitch):
    x, y, z = point
    yaw_rad = math.radians(yaw)
    pitch_rad = math.radians(pitch)

    cos_yaw = math.cos(yaw_rad)
    sin_yaw = math.sin(yaw_rad)
    xz = x * cos_yaw + z * sin_yaw
    zz = -x * sin_yaw + z * cos_yaw

    cos_pitch = math.cos(pitch_rad)
    sin_pitch = math.sin(pitch_rad)
    yz = y * cos_pitch - zz * sin_pitch
    zp = y * sin_pitch + zz * cos_pitch
    return xz, yz, zp


def _project(point, width, height, yaw, pitch, roll, zoom):
    x, y, z = _rotate(point, yaw, pitch)
    distance = 3.2
    denom = max(0.8, distance + z)
    scale = min(width, height) * (0.95 + float(zoom) * 0.07)
    px = x * scale / denom
    py = y * scale / denom

    roll_rad = math.radians(roll)
    cos_roll = math.cos(roll_rad)
    sin_roll = math.sin(roll_rad)
    rx = px * cos_roll - py * sin_roll
    ry = px * sin_roll + py * cos_roll

    return (
        width * 0.5 + rx,
        height * 0.56 - ry,
        z,
        scale / denom,
    )


def _point2(projected):
    return projected[0], projected[1]


def _draw_line(draw, start, end, width, fill):
    draw.line([_point2(start), _point2(end)], fill=fill, width=width, joint="curve")


def _arm_points(side, shoulder, arm_raise, elbow_bend):
    arm_raise = clamp(float(arm_raise), -90.0, 160.0)
    elbow_bend = clamp(float(elbow_bend), -80.0, 150.0)
    upper_len = 0.51
    lower_len = 0.49

    upper_angle = math.radians(arm_raise)
    elbow = (
        shoulder[0] + side * math.sin(upper_angle) * upper_len * 0.92,
        shoulder[1] - math.cos(upper_angle) * upper_len,
        shoulder[2] - 0.04,
    )

    lower_angle = math.radians(arm_raise - elbow_bend)
    wrist = (
        elbow[0] + side * math.sin(lower_angle) * lower_len * 0.92,
        elbow[1] - math.cos(lower_angle) * lower_len,
        elbow[2] - 0.04,
    )
    return elbow, wrist


def _leg_points(side, hip, leg_lift, knee_bend):
    leg_lift = clamp(float(leg_lift), -45.0, 90.0)
    knee_bend = clamp(float(knee_bend), -40.0, 120.0)
    upper_len = 0.66
    lower_len = 0.57

    upper_angle = math.radians(leg_lift)
    knee = (
        hip[0] + side * 0.02,
        hip[1] - math.cos(upper_angle) * upper_len,
        hip[2] - math.sin(upper_angle) * upper_len * 0.85 + 0.03,
    )

    lower_angle = math.radians(leg_lift - knee_bend)
    ankle = (
        knee[0] + side * 0.02,
        knee[1] - math.cos(lower_angle) * lower_len,
        knee[2] - math.sin(lower_angle) * lower_len * 0.85 - 0.07,
    )
    return knee, ankle


def build_body_points(
    left_arm_raise=DEFAULT_LEFT_ARM_RAISE,
    right_arm_raise=DEFAULT_RIGHT_ARM_RAISE,
    left_elbow_bend=DEFAULT_LEFT_ELBOW_BEND,
    right_elbow_bend=DEFAULT_RIGHT_ELBOW_BEND,
    left_leg_lift=DEFAULT_LEFT_LEG_LIFT,
    right_leg_lift=DEFAULT_RIGHT_LEG_LIFT,
    left_knee_bend=DEFAULT_LEFT_KNEE_BEND,
    right_knee_bend=DEFAULT_RIGHT_KNEE_BEND,
):
    joints = {
        "head": (0.0, 1.33, -0.02),
        "neck": (0.0, 1.05, 0.0),
        "chest": (0.0, 0.72, -0.02),
        "pelvis": (0.0, 0.0, 0.02),
        "chest_front": (0.0, 0.74, -0.16),
        "chest_back": (0.0, 0.74, 0.16),
        "pelvis_front": (0.0, 0.02, -0.12),
        "pelvis_back": (0.0, 0.02, 0.12),
        "left_shoulder": (-0.38, 0.94, 0.0),
        "right_shoulder": (0.38, 0.94, 0.0),
        "left_hip": (-0.24, 0.0, 0.02),
        "right_hip": (0.24, 0.0, 0.02),
        "nose": (0.0, 1.33, -0.28),
        "left_eye": (-0.07, 1.38, -0.22),
        "right_eye": (0.07, 1.38, -0.22),
        "mouth_left": (-0.06, 1.27, -0.22),
        "mouth_right": (0.06, 1.27, -0.22),
    }
    joints["left_elbow"], joints["left_wrist"] = _arm_points(
        -1,
        joints["left_shoulder"],
        left_arm_raise,
        left_elbow_bend,
    )
    joints["right_elbow"], joints["right_wrist"] = _arm_points(
        1,
        joints["right_shoulder"],
        right_arm_raise,
        right_elbow_bend,
    )
    joints["left_knee"], joints["left_ankle"] = _leg_points(
        -1,
        joints["left_hip"],
        left_leg_lift,
        left_knee_bend,
    )
    joints["right_knee"], joints["right_ankle"] = _leg_points(
        1,
        joints["right_hip"],
        right_leg_lift,
        right_knee_bend,
    )
    return joints


def render_angle_guide(
    width,
    height,
    yaw_degrees,
    pitch_degrees,
    roll_degrees,
    zoom,
    line_thickness=6,
    left_arm_raise=DEFAULT_LEFT_ARM_RAISE,
    right_arm_raise=DEFAULT_RIGHT_ARM_RAISE,
    left_elbow_bend=DEFAULT_LEFT_ELBOW_BEND,
    right_elbow_bend=DEFAULT_RIGHT_ELBOW_BEND,
    left_leg_lift=DEFAULT_LEFT_LEG_LIFT,
    right_leg_lift=DEFAULT_RIGHT_LEG_LIFT,
    left_knee_bend=DEFAULT_LEFT_KNEE_BEND,
    right_knee_bend=DEFAULT_RIGHT_KNEE_BEND,
):
    width = int(clamp(int(width), 256, 4096))
    height = int(clamp(int(height), 256, 4096))
    yaw = normalize_yaw(yaw_degrees)
    pitch = clamp(float(pitch_degrees), -75.0, 75.0)
    roll = clamp(float(roll_degrees), -45.0, 45.0)
    zoom = clamp(float(zoom), 0.0, 10.0)

    supersample = 2
    canvas_width = width * supersample
    canvas_height = height * supersample
    image = Image.new("RGB", (canvas_width, canvas_height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    line_width = max(1, int(line_thickness) * supersample)

    scaled_width = width * supersample
    scaled_height = height * supersample

    def project(point):
        return _project(
            point,
            scaled_width,
            scaled_height,
            yaw,
            pitch,
            roll,
            zoom,
        )

    joints = build_body_points(
        left_arm_raise,
        right_arm_raise,
        left_elbow_bend,
        right_elbow_bend,
        left_leg_lift,
        right_leg_lift,
        left_knee_bend,
        right_knee_bend,
    )
    projected = {name: project(point) for name, point in joints.items()}

    def segment_depth(segment):
        first, second, _color = segment
        return (projected[first][2] + projected[second][2]) * 0.5

    for segment in sorted(OPENPOSE_SEGMENTS, key=segment_depth, reverse=True):
        first, second, color = segment
        _draw_line(
            draw,
            projected[first],
            projected[second],
            line_width,
            color,
        )

    head = projected["head"]
    head_radius = max(10, int(0.18 * head[3]))
    head_box = [
        head[0] - head_radius,
        head[1] - head_radius * 1.12,
        head[0] + head_radius,
        head[1] + head_radius * 1.12,
    ]
    draw.ellipse(head_box, outline=(85, 0, 255), width=max(1, line_width // 2))

    yaw_rad = math.radians(yaw)
    front_visibility = math.cos(yaw_rad)
    side_visibility = abs(math.sin(yaw_rad))

    if front_visibility > 0.18:
        for eye_name in ("left_eye", "right_eye"):
            eye = projected[eye_name]
            radius = max(2, line_width // 3)
            draw.ellipse(
                [eye[0] - radius, eye[1] - radius, eye[0] + radius, eye[1] + radius],
                fill=(255, 255, 255),
            )
        _draw_line(
            draw,
            projected["mouth_left"],
            projected["mouth_right"],
            max(1, line_width // 2),
            (255, 255, 255),
        )
    elif side_visibility > 0.35 and front_visibility > -0.25:
        _draw_line(
            draw,
            projected["head"],
            projected["nose"],
            line_width,
            (170, 0, 255),
        )
    elif front_visibility < -0.18:
        back_top = project((0.0, 1.48, 0.12))
        back_low = project((0.0, 1.16, 0.14))
        _draw_line(
            draw,
            back_top,
            back_low,
            max(1, line_width // 2),
            (160, 160, 255),
        )

    for name in OPENPOSE_JOINTS:
        point = projected[name]
        radius = max(3, line_width // 2)
        draw.ellipse(
            [point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius],
            fill=(255, 255, 255),
        )

    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS
    return image.resize((width, height), resample)
