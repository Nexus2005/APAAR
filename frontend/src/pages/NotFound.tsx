import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Logo } from "../components/ui";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-paper px-6 text-center">
      <Logo />
      <p className="serif mt-10 text-[64px] leading-none text-brand">404</p>
      <h1 className="mt-2 text-[18px] font-bold text-ink">This page is not part of the prototype.</h1>
      <p className="mt-2 max-w-sm text-[12.5px] leading-relaxed text-ink-soft">
        Check the link, or head back to the console. Nothing was changed.
      </p>
      <Link to="/" className="btn-primary mt-6 text-xs"><ArrowLeft className="h-4 w-4" /> Back to safety</Link>
    </div>
  );
}
