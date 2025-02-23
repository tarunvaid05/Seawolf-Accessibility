"use client";
import Example from './components/example';

export default function HomePage() {
  return (
    <>
      <style jsx>{`
        @import url('https://fonts.googleapis.com/css2?family=Lilita+One&family=Lora:ital,wght@0,400..700;1,400..700&display=swap');

        h1 {
          padding-top: 1%;
          font-family: 'Lilita One', cursive;
          text-align: center;
          color: #0077be; /* Fallback color */
          font-size: 300%; /* 200% font size */
          margin: 1rem 0;
        }

        .gradient {
          background: linear-gradient(to right,rgb(152, 202, 231), #0077be);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .gradient1 {
          background: linear-gradient(to right, #0077be,rgb(152, 202, 231));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        
        p, body, html {
          font-family: 'Lora', serif;
        }
      `}</style>
      <style jsx global>{`
        html, body {
          margin: 0;
          padding: 0;
        }
      `}</style>

      <main
        style={{
          position: "relative",
          width: "100vw",
          height: "100vh",
          overflow: "hidden",
          margin: 0,
          padding: 0
        }}
      >
        <video
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            zIndex: -1
          }}
          autoPlay
          loop
          muted
        >
          <source src="/pics/waves (online-video-cutter.com).mp4" type="video/mp4" />
          Your browser does not support the video tag.
        </video>
        <h1>
          <span className="gradient">Sea</span>wolf Accessibil<span className="gradient1">ity</span>
        </h1>
        <Example />
      </main>
    </>
  );
}