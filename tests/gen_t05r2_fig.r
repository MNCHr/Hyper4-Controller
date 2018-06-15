require(plotrix)

# Load data
t05_data <- read.table("t05r2.dat",header=TRUE,sep=",")
t05p95_data <- read.table("t05r2p95.dat",header=TRUE,sep=",")

# Define colors
plot_colors <- c("black","red")

# Start pdf driver
pdf(file="t05r2.pdf", height=3.5, width=8)

# Trim excess margin space
par(mar=c(4.2, 3.9, 0.2, 0.5))

# Get range for x axis
max_x <- max(t05_data)
min_x <- min(t05_data)

# Plot
# ylim=c(0, 9)
plot(t05_data, type="p", pch=".", col=plot_colors[1], xlim=c(min_x, max_x), ann=FALSE)
points(t05p95_data, type="p", pch=".", col=plot_colors[2])

adj <- 0.85

# hosts reconfigured

end = 5
start = 0
l = 1
xpos = (end - start) / 2 + start

abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

interval = 10

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# IPv4 routers added
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

interval = 5

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# routers removed
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

interval = 10

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# add arp proxy, reconfigure hosts
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

interval = 5

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# switches removed
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# switches added back to end of chain
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# revert host configuration
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# add routers to end of chain
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# add firewall to end of alpha
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# remove routers
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# remove arp proxies
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1
draw.circle(x=xpos-adj,y=6,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=6, labels = l)

title(xlab="time (s)")
title(ylab="latency (ms)")

# Create legend
legend("topright", c(expression('individual latency, p'[i]), expression('95th percentile, (p'[i-1000]*',...,p'[i]*']')), col=plot_colors, pch=16, cex=0.8, box.lwd = 0, box.col = "white", bg = "white", inset=c(0.01, 0.01))

# Flush output to PDF
dev.off()

# Restore default margins
par(mar=c(5, 4, 4, 2) + 0.1)
