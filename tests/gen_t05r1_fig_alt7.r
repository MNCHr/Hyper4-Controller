require(plotrix)

# Load data
t05r1_data <- read.table("t05r1.dat",header=TRUE,sep=",")
t05r1p95_data <- read.table("t05r1p95.dat",header=TRUE,sep=",")

# Define colors
plot_colors <- c("black","red")

# Start pdf driver
pdf(file="t05.pdf", height=3.5, width=8)

# Trim excess margin space
par(mar=c(4.2, 3.9, 0.2, 0.5))

# Get range for x axis
max_x <- max(t05r1_data)
min_x <- min(t05r1_data)

# Plot
plot(t05r1_data, type="p", pch=".", col=plot_colors[1], xlim=c(min_x, max_x), ann=FALSE)
points(t05r1p95_data, type="p", pch=".", col=plot_colors[2])

adj <- 0.85

# hosts reconfigured
abline(v=5-adj,col="forestgreen",lty=3)
#symbols(x=2.5-adj, y=6, circles=c(0.25))
draw.circle(x=2.5-adj,y=6,radius=1,lty=1,lwd=1)
text(x=2.5-adj, y=6, labels = "1")

# IPv4 routers added
abline(v=15-adj, col="forestgreen", lty=3)


# routers removed
abline(v=20-adj, col="forestgreen", lty=3)

# add arp proxy, reconfigure hosts
abline(v=30-adj, col="forestgreen", lty=3)

# switches removed
abline(v=35-adj, col="forestgreen", lty=3)

# switches added back to end of chain
abline(v=40-adj, col="forestgreen", lty=3)

# revert host configuration
abline(v=45-adj, col="forestgreen", lty=3)

# add routers to end of chain
abline(v=50-adj, col="forestgreen", lty=3)

# add firewall to end of alpha
abline(v=55-adj, col="forestgreen", lty=3)

# remove routers
abline(v=60-adj, col="forestgreen", lty=3)

# remove arp proxies
abline(v=65-adj, col="forestgreen", lty=3)

title(xlab="time")
title(ylab="latency (ms)")

# Create legend
legend("topright", c("individual latency", "95th percentile of 1000 pings"), col=plot_colors, pch=16, cex=0.8, box.lwd = 0, box.col = "white", bg = "white", inset=c(0.01, 0.01))

# Flush output to PDF
dev.off()

# Restore default margins
par(mar=c(5, 4, 4, 2) + 0.1)
