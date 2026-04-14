const Badge = ({ children, variant = 'default', className = '' }) => {
  const styles = {
    success: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
    error: 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20',
    warning: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20',
    info: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20',
    default: 'bg-secondary text-muted-foreground border-border',
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${styles[variant] || styles.default} ${className}`}>
      {children}
    </span>
  )
}

export default Badge
