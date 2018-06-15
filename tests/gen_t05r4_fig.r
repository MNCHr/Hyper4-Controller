require(plotrix)

# Load data
t05_data <- read.table("t05r4iperf.dat",header=FALSE,sep="")

# Define colors
#plot_colors <- c("black","red")

# Start pdf driver
pdf(file="t05r4.pdf", height=3.5, width=8)

# Trim excess margin space
par(mar=c(4.2, 3.9, 0.2, 0.5))

# Get range for x axis
max_x <- max(t05_data[,4])
min_x <- min(t05_data[,4])

# Plot
plot(t05_data[,4], t05_data[,8], type="n", xlim=c(1, 70), ylim=c(0, 300), ann=FALSE)
lines(t05_data[,4], t05_data[,8], type="b", pch=20)

adj <- 1.5

# hosts reconfigured

end = 5
start = 0
l = 1
xpos = (end - start) / 2 + start

abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=40, labels = l)

interval = 10

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# IPv4 routers added
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=40, labels = l)

interval = 5

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# routers removed
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=20,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=20, labels = l)

interval = 10

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# add arp proxy, reconfigure hosts
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=40, labels = l)

interval = 5

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# switches removed
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=40, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# switches added back to end of chain
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=40, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# revert host configuration
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj+1,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj+1, y=40, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# add routers to end of chain
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=40, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# add firewall to end of alpha
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=40, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# remove routers
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=40, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1

# remove arp proxies
abline(v=end-adj,col="forestgreen",lty=3)
draw.circle(x=xpos-adj,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=40, labels = l)

start = end
end = end + interval
xpos = (end - start) / 2 + start
l = l + 1
draw.circle(x=xpos-adj,y=40,radius=1,lty=1,lwd=1)
text(x=xpos-adj, y=40, labels = l)

title(xlab="time (s)")
title(ylab="bandwidth (Mbps)")

# Flush output to PDF
dev.off()

# Restore default margins
par(mar=c(5, 4, 4, 2) + 0.1)
