const form = document.getElementById("uploadForm");
const progressBar = document.getElementById("progressBar");
const status = document.getElementById("status");
const originalSize = document.getElementById("originalSize");
const compressedSize = document.getElementById("compressedSize");
const downloadSection = document.getElementById("downloadSection");
const downloadBtn = document.getElementById("downloadBtn");

let jobId = "";

form.addEventListener("submit", function (e) {

    e.preventDefault();

    progressBar.style.width = "0%";
    progressBar.innerHTML = "0%";

    status.innerHTML = "Uploading Video...";
    downloadSection.style.display = "none";

    const formData = new FormData(form);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {

        jobId = data.job_id;

        originalSize.innerHTML = data.original_size;

        status.innerHTML = "Compressing Video...";

        checkProgress();

    })
    .catch(err => {

        console.log(err);

        alert("Upload Failed");

    });

});


function checkProgress() {

    let timer = setInterval(function () {

        fetch("/progress/" + jobId)

        .then(res => res.json())

        .then(data => {

            let value = data.progress;

            progressBar.style.width = value + "%";

            progressBar.innerHTML = value + "%";

            if (value >= 100) {

                clearInterval(timer);

                status.innerHTML = "Compression Completed";

                getResult();

            }

        });

    }, 1000);

}



function getResult() {

    fetch("/result/" + jobId)

    .then(res => res.json())

    .then(data => {

        if (data.ready) {

            compressedSize.innerHTML = data.compressed_size;

            downloadBtn.href = data.download;

            downloadSection.style.display = "block";

        } else {

            setTimeout(getResult, 1000);

        }

    });

}