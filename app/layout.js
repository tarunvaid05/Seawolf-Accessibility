export const metadata = {
    title: "Stony Brook Accessible Routes",
    description: "Minimal Next.js app for route computation."
  };
  
  export default function RootLayout({ children }) {
    return (
      <html lang="en">
        <body>
          {children}
        </body>
      </html>
    );
  }
  