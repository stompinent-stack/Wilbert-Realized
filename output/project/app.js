// ── TRACKS DATA ───────────────────────────────────────────────────────────────
const tracks = [
  { title: 'Midnight Dreams', artist: 'Luna Rose', emoji: '🌙', next: 'City Lights — Marco V' },
  { title: 'City Lights',     artist: 'Marco V',   emoji: '🌆', next: 'Golden Hour — Aisha J' },
  { title: 'Golden Hour',     artist: 'Aisha J',   emoji: '☀️', next: 'Neon Pulse — DJ Spark' },
  { title: 'Neon Pulse',      artist: 'DJ Spark',  emoji: '💜', next: 'Midnight Dreams — Luna Rose' },
  { title: 'Ocean Drive',     artist: 'Kai Storm',  emoji: '🌊', next: 'City Lights — Marco V' },
  { title: 'Fire & Ice',      artist: 'Zara Blue',  emoji: '🔥', next: 'Golden Hour — Aisha J' },
];

let currentTrack = 0;
let isPlaying = false;
let listenerCount = 12847;

// ── PLAYER ────────────────────────────────────────────────────────────────────
function togglePlayer() {
  const bar = document.getElementById('playerBar');
  bar.classList.add('active');
  isPlaying = true;
  updatePlayer();
  updatePlayBtn();
  document.body.style.paddingBottom = '90px';
}

function togglePlay() {
  isPlaying = !isPlaying;
  updatePlayBtn();
  const eq = document.getElementById('eq');
  if (isPlaying) eq.classList.remove('paused');
  else eq.classList.add('paused');
}

function updatePlayBtn() {
  const btn = document.getElementById('playBtn');
  if (btn) btn.textContent = isPlaying ? '⏸' : '▶';
}

function nextTrack() {
  currentTrack = (currentTrack + 1) % tracks.length;
  updatePlayer();
}

function prevTrack() {
  currentTrack = (currentTrack - 1 + tracks.length) % tracks.length;
  updatePlayer();
}

function updatePlayer() {
  const t = tracks[currentTrack];
  const titleEl = document.getElementById('trackTitle');
  const artistEl = document.getElementById('trackArtist');
  const nextEl = document.getElementById('nextTrack');
  if (titleEl) titleEl.textContent = t.title;
  if (artistEl) artistEl.textContent = t.artist;
  if (nextEl) nextEl.textContent = t.next;
}

function playTrack(title, artist) {
  const idx = tracks.findIndex(t => t.title === title);
  if (idx !== -1) currentTrack = idx;
  togglePlayer();
}

function setVolume(val) {
  console.log('Volume:', val);
}

// ── VOTING ────────────────────────────────────────────────────────────────────
function vote(btn, event) {
  event.stopPropagation();
  if (btn.classList.contains('voted')) {
    btn.classList.remove('voted');
    const num = parseInt(btn.textContent.replace(/[^\d]/g, '')) - 1;
    btn.textContent = '♥ ' + formatNum(num);
  } else {
    btn.classList.add('voted');
    const num = parseInt(btn.textContent.replace(/[^\d]/g, '')) + 1;
    btn.textContent = '♥ ' + formatNum(num);
  }
}

function formatNum(n) {
  return n >= 1000 ? (n/1000).toFixed(1) + 'K' : n;
}

// ── LISTENER COUNT ────────────────────────────────────────────────────────────
function updateListeners() {
  const delta = Math.floor(Math.random() * 20) - 8;
  listenerCount = Math.max(12000, listenerCount + delta);
  document.querySelectorAll('.live-count').forEach(el => {
    el.textContent = listenerCount.toLocaleString('nl-NL');
  });
}
setInterval(updateListeners, 4000);

// ── AUTO NEXT TRACK (elke 3 min simulatie — hier 30s voor demo) ───────────────
setInterval(() => {
  if (isPlaying) nextTrack();
}, 30000);

// ── FADE-IN SCROLL ────────────────────────────────────────────────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(el => {
    if (el.isIntersecting) {
      el.target.classList.add('visible');
      observer.unobserve(el.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.fade-up').forEach(el => observer.observe(el));

// ── SMOOTH SCROLL ─────────────────────────────────────────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const target = document.querySelector(a.getAttribute('href'));
    if (target) target.scrollIntoView({ behavior: 'smooth' });
  });
});

// ── NAVBAR SCROLL EFFECT ──────────────────────────────────────────────────────
window.addEventListener('scroll', () => {
  const nav = document.querySelector('nav');
  if (nav) {
    if (window.scrollY > 50) {
      nav.style.background = 'rgba(6,6,15,0.97)';
    } else {
      nav.style.background = 'rgba(6,6,15,0.85)';
    }
  }
});

// ── INIT ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updatePlayer();
  console.log('🎵 Big Tunes Radio — Live');
});
