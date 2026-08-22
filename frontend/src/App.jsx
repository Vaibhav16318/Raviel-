import React, { useEffect, useRef, useState } from "react";
import "./styles.css";

const API = "https://rag-goa-black.vercel.app";

const IDLE = "idle";
const LISTENING = "listening";
const THINKING = "thinking";
const SPEAKING = "speaking";


// ============================================================
// VISUAL
// ============================================================

function RAVIELVisual({ state, onMic }) {
  const canvasRef = useRef(null);
  const stateRef = useRef(state);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    let w = 0;
    let h = 0;
    let dpr = 1;
    let animationFrame;

    const stars = [];
    const squares = [];
    const sphereNodes = [];
    const orbits = [];

    // ----------------------------------------------------------
    // RESIZE
    // ----------------------------------------------------------

    function resize() {
      const rect = canvas.getBoundingClientRect();

      w = rect.width;
      h = rect.height;

      dpr = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    resize();

    window.addEventListener("resize", resize);


    // ----------------------------------------------------------
    // BACKGROUND STARS
    // ----------------------------------------------------------

    for (let i = 0; i < 520; i++) {
      stars.push({
        x: Math.random(),
        y: Math.random(),
        size:
          Math.random() < 0.08
            ? 2.5 + Math.random() * 3.5
            : 0.6 + Math.random() * 2.2,
        alpha: 0.25 + Math.random() * 0.65,
        speed: 0.000003 + Math.random() * 0.000012,
        phase: Math.random() * Math.PI * 2,
      });
    }


    // ----------------------------------------------------------
    // FLOATING SQUARES
    // ----------------------------------------------------------

    for (let i = 0; i < 190; i++) {
      const angle =
        Math.random() * Math.PI * 2;

      const distance =
        0.72 + Math.random() * 0.78;

      squares.push({
        angle,
        distance,

        speed:
          (0.00008 +
            Math.random() * 0.00035) *
          (Math.random() < 0.5 ? 1 : -1),

        size:
          Math.random() < 0.08
            ? 10 + Math.random() * 13
            : Math.random() < 0.3
              ? 5 + Math.random() * 7
              : 1.5 + Math.random() * 4,

        alpha:
          0.25 + Math.random() * 0.7,

        vertical:
          -0.15 +
          Math.random() * 0.3,

        drift:
          Math.random() * Math.PI * 2,

        hue:
          Math.random() < 0.78
            ? "cyan"
            : Math.random() < 0.5
              ? "white"
              : "orange",
      });
    }


    // ----------------------------------------------------------
    // SMALL SPHERE NODES
    // ----------------------------------------------------------

    for (let i = 0; i < 100; i++) {
      const theta =
        Math.random() * Math.PI * 2;

      const phi =
        Math.acos(
          2 * Math.random() - 1
        );

      sphereNodes.push({
        theta,
        phi,
        size:
          1 + Math.random() * 3.5,
        alpha:
          0.18 + Math.random() * 0.55,
      });
    }


    // ----------------------------------------------------------
    // ORBITS
    // ----------------------------------------------------------

    for (let i = 0; i < 5; i++) {
      orbits.push({
        rotation:
          Math.random() * Math.PI,
        speed:
          0.00002 +
          Math.random() * 0.00004,
        flatten:
          0.22 +
          Math.random() * 0.2,
      });
    }


    // ==========================================================
    // COLORS
    // ==========================================================

    function colors(mode) {
      if (mode === LISTENING) {
        return {
          primary: [55, 205, 255],
          bright: [175, 245, 255],
          square: [105, 225, 245],
        };
      }

      if (
        mode === THINKING ||
        mode === SPEAKING
      ) {
        return {
          primary: [65, 190, 240],
          bright: [215, 250, 255],
          square: [115, 230, 250],
        };
      }

      return {
        primary: [232, 92, 32],
        bright: [255, 155, 75],
        square: [90, 205, 220],
      };
    }


    // ==========================================================
    // SPHERE
    // ==========================================================

    function drawSphere(
      cx,
      cy,
      radius,
      mode,
      time
    ) {
      const c = colors(mode);

      const [r, g, b] =
        c.primary;

      const [br, bg, bb] =
        c.bright;


      // --------------------------------------------------------
      // SOFT SPHERE GLOW
      // --------------------------------------------------------

      const glow =
        ctx.createRadialGradient(
          cx,
          cy,
          radius * 0.7,
          cx,
          cy,
          radius * 1.1
        );

      glow.addColorStop(
        0,
        `rgba(${r},${g},${b},0.025)`
      );

      glow.addColorStop(
        0.75,
        `rgba(${r},${g},${b},0.04)`
      );

      glow.addColorStop(
        1,
        "rgba(0,0,0,0)"
      );

      ctx.fillStyle = glow;

      ctx.beginPath();

      ctx.arc(
        cx,
        cy,
        radius * 1.1,
        0,
        Math.PI * 2
      );

      ctx.fill();


      // --------------------------------------------------------
      // DENSE LATITUDE GRID
      // --------------------------------------------------------

      ctx.save();

      ctx.lineWidth =
        mode === IDLE
          ? 0.42
          : 0.65;

      for (
        let i = -34;
        i <= 34;
        i++
      ) {
        const lat = i / 34;

        const y =
          cy + lat * radius;

        const rx =
          radius *
          Math.sqrt(
            Math.max(
              0,
              1 - lat * lat
            )
          );

        if (rx < 2) continue;

        ctx.beginPath();

        ctx.ellipse(
          cx,
          y,
          rx,
          Math.max(
            0.8,
            rx * 0.035
          ),
          0,
          0,
          Math.PI * 2
        );

        ctx.strokeStyle =
          `rgba(${r},${g},${b},${
            0.16 +
            (1 - Math.abs(lat)) *
              0.13
          })`;

        ctx.stroke();
      }

      ctx.restore();


      // --------------------------------------------------------
      // DENSE LONGITUDE GRID
      // --------------------------------------------------------

      ctx.save();

      ctx.lineWidth =
        mode === IDLE
          ? 0.42
          : 0.62;

      for (
        let i = 0;
        i < 68;
        i++
      ) {
        const angle =
          (i / 68) *
          Math.PI;

        const rx =
          Math.abs(
            Math.sin(angle)
          ) * radius;

        if (rx < 1) continue;

        ctx.beginPath();

        ctx.ellipse(
          cx,
          cy,
          rx,
          radius,
          0,
          0,
          Math.PI * 2
        );

        ctx.strokeStyle =
          `rgba(${r},${g},${b},0.18)`;

        ctx.stroke();
      }

      ctx.restore();


      // --------------------------------------------------------
      // DIAGONAL NETWORK
      // --------------------------------------------------------

      ctx.save();

      ctx.lineWidth = 0.35;

      for (
        let i = -16;
        i < 17;
        i++
      ) {
        ctx.beginPath();

        ctx.moveTo(
          cx - radius,
          cy +
            i *
              radius *
              0.055
        );

        ctx.lineTo(
          cx + radius,
          cy -
            i *
              radius *
              0.055
        );

        ctx.strokeStyle =
          `rgba(${r},${g},${b},0.045)`;

        ctx.stroke();
      }

      ctx.restore();


      // --------------------------------------------------------
      // SPHERE EDGE
      // --------------------------------------------------------

      ctx.save();

      ctx.beginPath();

      ctx.arc(
        cx,
        cy,
        radius,
        0,
        Math.PI * 2
      );

      ctx.strokeStyle =
        `rgba(${br},${bg},${bb},0.95)`;

      ctx.lineWidth =
        mode === IDLE
          ? 2
          : 2.8;

      ctx.shadowBlur =
        mode === IDLE
          ? 14
          : 28;

      ctx.shadowColor =
        `rgba(${r},${g},${b},0.7)`;

      ctx.stroke();

      ctx.restore();


      // --------------------------------------------------------
      // SPHERE NODES
      // --------------------------------------------------------

      for (const node of sphereNodes) {
        const spin =
          node.theta +
          time * 0.00004;

        const sinPhi =
          Math.sin(node.phi);

        const x3 =
          sinPhi *
          Math.cos(spin);

        const y3 =
          Math.cos(node.phi);

        const z3 =
          sinPhi *
          Math.sin(spin);

        const perspective =
          0.72 +
          z3 * 0.28;

        const x =
          cx +
          x3 *
            radius *
            perspective;

        const y =
          cy +
          y3 *
            radius *
            perspective;

        const size =
          node.size *
          perspective;

        ctx.fillStyle =
          `rgba(${c.square[0]},${c.square[1]},${c.square[2]},${node.alpha * (0.35 + perspective * 0.65)})`;

        ctx.fillRect(
          x - size / 2,
          y - size / 2,
          size,
          size
        );
      }
    }


    // ==========================================================
    // OUTSIDE SQUARES
    // ==========================================================

    function drawSquares(
      cx,
      cy,
      radius,
      mode,
      time
    ) {
      const active =
        mode !== IDLE;

      for (const p of squares) {
        p.angle +=
          p.speed *
          (active ? 2.3 : 0.7);

        p.drift +=
          0.0005;


        const rr =
          radius *
          p.distance;


        const wobble =
          Math.sin(
            time * 0.001 +
            p.drift
          ) *
          radius *
          p.vertical;


        const x =
          cx +
          Math.cos(
            p.angle
          ) *
            rr;


        const y =
          cy +
          Math.sin(
            p.angle
          ) *
            rr *
            0.52 +
          wobble;


        let color;

        if (
          p.hue === "orange"
        ) {
          color =
            "255,145,70";
        } else if (
          p.hue === "white"
        ) {
          color =
            "225,245,245";
        } else {
          color =
            "85,210,225";
        }


        let alpha =
          p.alpha;


        // Fade squares that are very far away.
        const normalized =
          p.distance;

        if (
          normalized > 1.25
        ) {
          alpha *= 0.7;
        }


        ctx.fillStyle =
          `rgba(${color},${alpha})`;


        ctx.fillRect(
          x - p.size / 2,
          y - p.size / 2,
          p.size,
          p.size
        );
      }
    }


    // ==========================================================
    // ORBIT LINES
    // ==========================================================

    function drawOrbits(
      cx,
      cy,
      radius,
      mode,
      time
    ) {
      for (
        let i = 0;
        i < orbits.length;
        i++
      ) {
        const o = orbits[i];

        o.rotation +=
          o.speed *
          (mode === IDLE
            ? 0.7
            : 1.5);

        ctx.save();

        ctx.translate(
          cx,
          cy
        );

        ctx.rotate(
          o.rotation
        );

        ctx.translate(
          -cx,
          -cy
        );

        ctx.beginPath();

        ctx.ellipse(
          cx,
          cy,
          radius *
            (1.15 + i * 0.08),
          radius *
            o.flatten,
          0,
          0,
          Math.PI * 2
        );

        ctx.strokeStyle =
          mode === IDLE
            ? "rgba(40,100,110,0.12)"
            : "rgba(55,180,220,0.16)";

        ctx.lineWidth =
          0.7;

        ctx.stroke();

        ctx.restore();
      }
    }


    // ==========================================================
    // BOTTOM WAVEFORM
    // ==========================================================

    function drawWave(
      cx,
      cy,
      radius,
      mode,
      time
    ) {
      const active =
        mode !== IDLE;

      const count = 72;

      for (
        let i = 0;
        i < count;
        i++
      ) {
        const x =
          cx -
          radius * 0.34 +
          (i / count) *
            radius *
            0.68;

        const wave =
          Math.sin(
            time * 0.01 +
            i * 0.45
          );

        let height =
          active
            ? 5 +
              Math.abs(wave) *
                18
            : 2 +
              Math.abs(wave) *
                4;

        if (
          mode === SPEAKING
        ) {
          height *=
            1.25;
        }

        ctx.fillStyle =
          mode === IDLE
            ? "rgba(50,125,135,0.35)"
            : "rgba(55,210,225,0.7)";

        ctx.fillRect(
          x,
          cy +
            radius *
              0.97 -
            height,
          1.5,
          height
        );
      }
    }


    // ==========================================================
    // MICROPHONE
    // ==========================================================

    function drawMic(
      cx,
      cy,
      mode
    ) {
      const active =
        mode === LISTENING ||
        mode === SPEAKING ||
        mode === THINKING;

      const color =
        active
          ? "#66eaff"
          : "#36aab7";

      const glow =
        active
          ? "rgba(80,230,255,0.7)"
          : "rgba(40,170,190,0.3)";

      ctx.save();

      ctx.beginPath();

      ctx.arc(
        cx,
        cy,
        24,
        0,
        Math.PI * 2
      );

      ctx.fillStyle =
        "rgba(0,8,10,0.88)";

      ctx.fill();

      ctx.strokeStyle =
        active
          ? "rgba(80,230,255,0.65)"
          : "rgba(60,150,160,0.25)";

      ctx.lineWidth = 1;

      ctx.stroke();


      // microphone capsule
      ctx.beginPath();

      ctx.roundRect(
        cx - 5,
        cy - 10,
        10,
        17,
        5
      );

      ctx.strokeStyle =
        color;

      ctx.lineWidth = 1.4;

      ctx.shadowBlur =
        active ? 10 : 3;

      ctx.shadowColor =
        glow;

      ctx.stroke();


      // microphone arc
      ctx.beginPath();

      ctx.arc(
        cx,
        cy + 1,
        10,
        0,
        Math.PI
      );

      ctx.stroke();


      // stem
      ctx.beginPath();

      ctx.moveTo(
        cx,
        cy + 11
      );

      ctx.lineTo(
        cx,
        cy + 15
      );

      ctx.moveTo(
        cx - 5,
        cy + 16
      );

      ctx.lineTo(
        cx + 5,
        cy + 16
      );

      ctx.stroke();

      ctx.restore();
    }


    // ==========================================================
    // ANIMATION LOOP
    // ==========================================================

    function animate(time) {
      const mode =
        stateRef.current;

      ctx.clearRect(
        0,
        0,
        w,
        h
      );

      ctx.fillStyle =
        "#000304";

      ctx.fillRect(
        0,
        0,
        w,
        h
      );


      // --------------------------------------------------------
      // STARS
      // --------------------------------------------------------

      for (const star of stars) {
        star.y -=
          star.speed;

        if (
          star.y < -0.01
        ) {
          star.y = 1.01;
        }

        const pulse =
          0.75 +
          Math.sin(
            time * 0.002 +
            star.phase
          ) *
            0.25;

        ctx.fillStyle =
          `rgba(175,200,205,${
            star.alpha * pulse
          })`;

        ctx.fillRect(
          star.x * w,
          star.y * h,
          star.size,
          star.size
        );
      }


      const cx =
        w / 2;

      const cy =
        h * 0.49;

      const radius =
        Math.min(
          w,
          h
        ) * 0.355;


      // back orbital structure
      drawOrbits(
        cx,
        cy,
        radius,
        mode,
        time
      );


      // floating squares
      drawSquares(
        cx,
        cy,
        radius,
        mode,
        time
      );


      // main sphere
      drawSphere(
        cx,
        cy,
        radius,
        mode,
        time
      );


      // waveform
      drawWave(
        cx,
        cy,
        radius,
        mode,
        time
      );


      // bottom microphone
      drawMic(
        cx,
        Math.min(
          h - 38,
          cy +
            radius +
            38
        ),
        mode
      );


      animationFrame =
        requestAnimationFrame(
          animate
        );
    }


    animationFrame =
      requestAnimationFrame(
        animate
      );


    return () => {
      cancelAnimationFrame(
        animationFrame
      );

      window.removeEventListener(
        "resize",
        resize
      );
    };
  }, []);


  return (
    <canvas
      ref={canvasRef}
      className="raviel-canvas"
      onClick={onMic}
    />
  );
}


// ============================================================
// VOICE
// ============================================================

function useVoice() {
  const recognitionRef =
    useRef(null);

  const requestRef =
    useRef(null);

  const [state, setState] =
    useState(IDLE);


  useEffect(() => {
    return () => {
      try {
        recognitionRef.current?.abort();
      } catch {}

      try {
        requestRef.current?.abort();
      } catch {}

      try {
        window.speechSynthesis.cancel();
      } catch {}
    };
  }, []);


  function speak(text) {
    if (!text?.trim()) {
      setState(IDLE);
      return;
    }

    window.speechSynthesis.cancel();

    const utterance =
      new SpeechSynthesisUtterance(
        text.trim()
      );

    utterance.lang =
      "en-US";

    utterance.rate =
      1.25;

    utterance.pitch =
      0.96;

    utterance.volume = 1;


    utterance.onstart =
      () => {
        setState(SPEAKING);
      };


    utterance.onend =
      () => {
        setState(IDLE);
      };


    utterance.onerror =
      () => {
        setState(IDLE);
      };


    window.speechSynthesis.speak(
      utterance
    );
  }


  async function ask(
    query
  ) {
    const controller =
      new AbortController();

    requestRef.current =
      controller;

    setState(THINKING);


    try {
      const response =
        await fetch(
          `${API}/ask`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              query,
            }),

            signal:
              controller.signal,
          }
        );


      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }


      const data =
        await response.json();


      const answer =
        data?.answer?.trim();


      if (!answer) {
        throw new Error(
          "Empty answer"
        );
      }


      speak(answer);

    } catch (error) {
      if (
        error.name ===
        "AbortError"
      ) {
        return;
      }

      console.error(
        "[RAVIEL]",
        error
      );

      speak(
        "I could not connect to the intelligence system."
      );

    } finally {
      requestRef.current =
        null;
    }
  }


  function startListening() {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;


    if (!SpeechRecognition) {
      console.error(
        "Speech recognition is not supported."
      );

      return;
    }


    try {
      recognitionRef.current?.abort();
    } catch {}


    window.speechSynthesis.cancel();


    const recognition =
      new SpeechRecognition();


    // ENGLISH ONLY
    recognition.lang =
      "en-US";

    recognition.continuous =
      false;

    recognition.interimResults =
      false;

    recognition.maxAlternatives =
      1;


    recognition.onstart =
      () => {
        setState(LISTENING);
      };


    recognition.onresult =
      event => {
        const transcript =
          event
            ?.results?.[0]?.[0]
            ?.transcript
            ?.trim();


        if (!transcript) {
          setState(IDLE);
          return;
        }


        try {
          recognition.stop();
        } catch {}


        ask(transcript);
      };


    recognition.onerror =
      event => {
        console.error(
          "[RAVIEL] microphone:",
          event.error
        );

        setState(IDLE);
      };


    recognition.onend =
      () => {
        setState(
          current =>
            current === LISTENING
              ? IDLE
              : current
        );
      };


    recognitionRef.current =
      recognition;


    try {
      recognition.start();
    } catch (error) {
      console.error(
        "[RAVIEL]",
        error
      );

      setState(IDLE);
    }
  }


  function toggle() {
    if (
      state === THINKING ||
      state === SPEAKING
    ) {
      return;
    }


    if (
      state === LISTENING
    ) {
      try {
        recognitionRef.current?.stop();
      } catch {}

      setState(IDLE);

      return;
    }


    startListening();
  }


  return {
    state,
    toggle,
  };
}


// ============================================================
// APP
// ============================================================

export default function App() {
  const {
    state,
    toggle,
  } = useVoice();


  return (
    <main className="raviel-app">
      <RAVIELVisual
        state={state}
        onMic={toggle}
      />
    </main>
  );
}