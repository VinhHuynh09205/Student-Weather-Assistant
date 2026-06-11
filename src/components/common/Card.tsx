import type { PropsWithChildren } from "react";

type CardProps = PropsWithChildren<{
  className?: string;
  title?: string;
}>;

export function Card({ children, className = "", title }: CardProps) {
  return (
    <section className={`glass-card ${className}`}>
      {title ? <h2 className="card-title">{title}</h2> : null}
      {children}
    </section>
  );
}
