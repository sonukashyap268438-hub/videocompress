import os
import uuid
import threading
import subprocess
import re

from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "compressed"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

progress = {}


def get_filesize(path):
    size = os.path.getsize(path)

    if size < 1024:
        return f"{size} Bytes"
    elif size < 1024 ** 2:
        return f"{round(size / 1024, 2)} KB"
    elif size < 1024 ** 3:
        return f"{round(size / 1024 ** 2, 2)} MB"
    else:
        return f"{round(size / 1024 ** 3, 2)} GB"


def get_duration(video_path):
    """
    Return video duration in seconds using ffprobe
    """

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        return float(result.stdout.strip())
    except:
        return 0


def time_to_seconds(t):

    h, m, s = t.split(":")

    return int(h) * 3600 + int(m) * 60 + float(s)


def compress_video(job_id, input_file, output_file, mode):

    if mode == "small":
        crf = "23"
        preset = "medium"

    elif mode == "medium":
        crf = "28"
        preset = "fast"

    else:
        crf = "35"
        preset = "veryfast"

    total_duration = get_duration(input_file)

    progress[job_id] = 0

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-vcodec",
        "libx264",
        "-crf",
        crf,
        "-preset",
        preset,
        "-acodec",
        "aac",
        output_file,
    ]

    process = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        universal_newlines=True,
        encoding="utf-8",
        errors="ignore",
    )

    regex = re.compile(r"time=(\d+:\d+:\d+\.\d+)")

    while True:

        line = process.stderr.readline()

        if not line:

            if process.poll() is not None:
                break

            continue

        match = regex.search(line)

        if match:

            current_time = time_to_seconds(match.group(1))

            if total_duration > 0:

                percent = int((current_time / total_duration) * 100)

                if percent > 100:
                    percent = 100

                progress[job_id] = percent

    process.wait()

    if process.returncode == 0:
        progress[job_id] = 100
    else:
        progress[job_id] = -1

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():

    if "video" not in request.files:
        return jsonify({"error": "No video selected"})

    video = request.files["video"]

    mode = request.form.get("mode", "medium")

    ext = os.path.splitext(video.filename)[1]

    uid = str(uuid.uuid4())

    input_path = os.path.join(UPLOAD_FOLDER, uid + ext)

    output_path = os.path.join(OUTPUT_FOLDER, uid + ".mp4")

    video.save(input_path)

    threading.Thread(
        target=compress_video,
        args=(uid, input_path, output_path, mode),
        daemon=True
    ).start()

    return jsonify({

        "job_id": uid,

        "original_size": get_filesize(input_path)

    })


@app.route("/progress/<job_id>")
def get_progress(job_id):

    value = progress.get(job_id, 0)

    return jsonify({

        "progress": value

    })


@app.route("/result/<job_id>")
def result(job_id):

    filename = job_id + ".mp4"

    path = os.path.join(OUTPUT_FOLDER, filename)

    if progress.get(job_id, 0) < 100:

        return jsonify({

            "ready": False

        })

    if not os.path.exists(path):

        return jsonify({

            "ready": False

        })

    original_file = None

    for f in os.listdir(UPLOAD_FOLDER):

        if f.startswith(job_id):

            original_file = os.path.join(UPLOAD_FOLDER, f)

            break

    original_size = ""

    if original_file and os.path.exists(original_file):

        original_size = get_filesize(original_file)

    return jsonify({

        "ready": True,

        "original_size": original_size,

        "compressed_size": get_filesize(path),

        "download": "/download/" + filename

    })


@app.route("/download/<filename>")
def download(filename):

    return send_from_directory(

        OUTPUT_FOLDER,

        filename,

        as_attachment=True

    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )