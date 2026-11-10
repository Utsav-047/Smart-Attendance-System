/**
 * Smart Attendance System - Student Biometric Face Registration (register.js)
 */

let stream = null;
let capturedFrames = [];

async function startCamera() {
  const rollInput = document.getElementById('roll');
  if (!rollInput.value.trim()) {
    alert('Please enter your Student ID / Roll Number before activating the camera.');
    rollInput.focus();
    return;
  }

  const video = document.getElementById('webcamVideo');
  const placeholder = document.getElementById('cameraPlaceholder');
  const guide = document.getElementById('faceGuide');
  const captureBtn = document.getElementById('captureBtn');
  const startCamBtn = document.getElementById('startCamBtn');

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false
    });
    video.srcObject = stream;
    video.classList.remove('hidden');
    guide.classList.remove('hidden');
    placeholder.classList.add('hidden');
    captureBtn.disabled = false;
    startCamBtn.innerHTML = '<i class="fa-solid fa-rotate-right text-xs"></i> Reset Camera';
  } catch (err) {
    alert('Could not access camera: ' + err.message + '\nPlease check camera permissions.');
  }
}

async function performCapture() {
  const roll = document.getElementById('roll').value.trim();
  if (!roll) {
    alert('Roll number is missing.');
    return;
  }

  const video = document.getElementById('webcamVideo');
  const canvas = document.getElementById('snapshotCanvas');
  const overlay = document.getElementById('capturingOverlay');
  const progressText = document.getElementById('captureProgressText');
  const guide = document.getElementById('faceGuide');
  const captureBtn = document.getElementById('captureBtn');

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');

  capturedFrames = [];
  overlay.classList.remove('hidden');
  guide.classList.add('active');
  captureBtn.disabled = true;

  const totalFrames = 5;
  for (let i = 1; i <= totalFrames; i++) {
    progressText.innerText = `Capturing sample ${i} of ${totalFrames}...`;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    capturedFrames.push(dataUrl);
    await new Promise(r => setTimeout(r, 400));
  }

  progressText.innerText = 'Analyzing face biometrics...';

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

  // Send to WebRTC capture endpoint
  try {
    const response = await fetch('/api/capture-webrtc', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ roll: roll, frames: capturedFrames })
    });
    const result = await response.json();

    overlay.classList.add('hidden');

    if (result.success) {
      document.getElementById('faceCapturedInput').value = '1';
      document.getElementById('successOverlay').classList.remove('hidden');
      document.getElementById('samplesCountLabel').innerText = `${result.saved_count} face samples encoded`;

      const badge = document.getElementById('captureStatusBadge');
      badge.className = 'text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800';
      badge.innerText = 'Verified';

      // Stop webcam stream cleanly
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    } else {
      guide.classList.remove('active');
      captureBtn.disabled = false;
      alert('Face capture issue: ' + (result.message || 'No face found in frames. Please align face inside the frame.'));
    }
  } catch (err) {
    overlay.classList.add('hidden');
    guide.classList.remove('active');
    captureBtn.disabled = false;
    alert('Network error connecting to capture API: ' + err.message);
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const regForm = document.getElementById('registrationForm');
  if (regForm) {
    regForm.addEventListener('submit', function (e) {
      const faceCaptured = document.getElementById('faceCapturedInput').value;
      if (faceCaptured !== '1') {
        e.preventDefault();
        alert('Please complete the Facial Biometric Setup by clicking "Capture & Verify Face" before submitting.');
        return false;
      }
      const submitBtn = document.getElementById('submitRegBtn');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-xs"></i> Saving & Encoding...';
    });
  }
});

