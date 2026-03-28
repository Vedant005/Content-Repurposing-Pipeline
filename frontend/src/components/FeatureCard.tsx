interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  figure: string;
}

const FeatureCard = ({
  icon,
  title,
  description,
  figure,
}: FeatureCardProps) => {
  return (
    <div className="border border-foreground p-6 hover:bg-secondary transition-colors duration-200 group">
      <div className="border border-foreground h-12 w-12 flex items-center justify-center mb-4 group-hover:bg-foreground group-hover:text-primary-foreground transition-colors">
        {icon}
      </div>
      <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        {figure}
      </span>
      <h3 className="font-serif text-xl font-bold mt-1 mb-2">{title}</h3>
      <p className="font-body text-sm text-muted-foreground leading-relaxed">
        {description}
      </p>
    </div>
  );
};

export default FeatureCard;
