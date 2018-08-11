require(plotrix)

#start h2 54:48 						 0
#start h3 54:49 						 1
#A: start h1 54:50 					 2
#start h6 54:51 						 3
#B: start h5 54:52 					 4
#C: start vib 54:59 		 		11
#D: complete vib 55:31 	 		43
#E: start rotation 55:38 		50
#F: complete rotation 56:16 88
#stop xterms 56:30 		  	 102

# Load data
t09_l2_addresses <- read.table("t09_analysis_l2_addresses_r1",header=TRUE,sep=",")
t09_l3_addresses <- read.table("t09_analysis_l3_addresses_r1",header=TRUE,sep=",")
t09_h2latency <-read.table("t09_analysis_latency_r1",header=TRUE,sep=",")
t09_h2latency_p95 <- read.table("t09_analysis_latency_p95_r1",header=TRUE,sep=",")
t09_h1bandwidth <- read.table("t09_analysis_h1bandwidth_r1",header=TRUE,sep=",")
t09_h5bandwidth <- read.table("t09_analysis_h5bandwidth_r1",header=TRUE,sep=",")

phvals1=c(2, 11, 43, 50, 88)
phlabels1=c("A", "C", "D", "E", "F")
phvals2=c(4)
phlabels2=c("B")

# Start pdf driver
pdf(file="t09_l2_addresses_r1.pdf", height=4, width=8)

#dev.new(width=8, height=4)

# Trim excess margin space
par(mar=c(4.2, 3.9, 0.2, 0.5))

# Get range
max_y <- max(t09_l2_addresses)

plot_colors <- c("black","red")

# Plot
plot(t09_l2_addresses, type="p", pch=".", col=plot_colors[1], ann=FALSE, yaxt="n", mgp=c(3, 0.5, 0))

maclabels <- c("00:*","20:*","40:*","60:*","80:*","A0:*","C0:*","E0:*")
macvals <- c(0, max_y/8, 2*max_y/8, 3*max_y/8, 4*max_y/8, 5*max_y/8, 6*max_y/8, 7*max_y/8)
axis(2,at=macvals,labels=maclabels,las=2)

adj <- 0

# lty 3 == dotted
# mark start h1
#abline(v=2,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=2-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=2-adj,y=0.75*max_y,labels = "A")

# mark start h5
#abline(v=4,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=4-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=4-adj,y=0.75*max_y,labels = "B")

# mark start vib
#abline(v=11,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=11-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=11-adj,y=0.75*max_y,labels = "C")

# mark complete vib
#abline(v=43,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=43-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=43-adj,y=0.75*max_y,labels = "D")

# mark start rotation
#abline(v=50,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=50-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=50-adj,y=0.75*max_y,labels = "E")

# mark complete rotation
#abline(v=88,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=88-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=88-adj,y=0.75*max_y,labels = "F")

title(xlab="time (s)")
title(ylab="MAC address")

# Flush output to PDF
dev.off()

#dev.new(width=8, height=4)

# Start pdf driver
pdf(file="t09_l3_addresses_r1.pdf", height=4, width=8)

# Get range
max_y <- max(t09_l3_addresses)

# Plot
plot(t09_l3_addresses, type="p", pch=".", col=plot_colors[1], ann=FALSE, yaxt="n", mgp=c(3, 0.5, 0))

iplabels <- c("0.*","32.*","64.*","96.*","128.*","160.*","192.*","224.*")
ipvals <- c(0, max_y/8, 2*max_y/8, 3*max_y/8, 4*max_y/8, 5*max_y/8, 6*max_y/8, 7*max_y/8)
axis(2,at=ipvals,labels=iplabels,las=2, cex.axis=0.5)

# lty 3 == dotted
# mark start h1
#abline(v=2,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=2-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=2-adj,y=0.75*max_y,labels = "A")

# mark start h5
#abline(v=4,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=4-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=4-adj,y=0.75*max_y,labels = "B")

# mark start vib
#abline(v=11,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=11-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=11-adj,y=0.75*max_y,labels = "C")

# mark complete vib
#abline(v=43,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=43-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=43-adj,y=0.75*max_y,labels = "D")

# mark start rotation
#abline(v=50,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=50-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=50-adj,y=0.75*max_y,labels = "E")

# mark complete rotation
#abline(v=88,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=88-adj,y=0.75*max_y,radius=1.25,lty=1,lwd=1,col="white")
text(x=88-adj,y=0.75*max_y,labels = "F")

title(xlab="time (s)")
title(ylab="IP address")

# Flush output to PDF
dev.off()

# Start pdf driver
pdf(file="t09_h1bandwidth_r1.pdf", height=4, width=8)

max_y_h1 <- max(t09_h1bandwidth[[2]])
max_y_h5 <- max(t09_h5bandwidth[[2]])
max_y <- max(max_y_h1,max_y_h5)

min_y_h1 <- min(t09_h1bandwidth[[2]])
min_y_h5 <- min(t09_h5bandwidth[[2]])
min_y <- min(min_y_h1,min_y_h5)

max_x <- max(t09_h1bandwidth[[1]])

# Plot
#plot(t05_data[,4], t05_data[,8], type="n", xlim=c(min_x, max_x), ann=FALSE)
plot(t09_h1bandwidth, type="n", col=plot_colors[1], ann=FALSE, mgp=c(3, 0.5, 0), ylim=c(min_y, max_y), xlim=c(0, max_x))
lines(t09_h1bandwidth, type="b", pch=20)
axis(1,at=phvals1,labels=phlabels1,las=1,mgp=c(3, 1.5, 0))
axis(1,at=phvals2,labels=phlabels2,las=1,mgp=c(3, 1.5, 0))

# lty 3 == dotted
# mark start h1
#abline(v=2,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=2-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=2-adj,y=30,labels = "A")

# mark start h5
#abline(v=4,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=4-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=4-adj,y=30,labels = "B")

# mark start vib
#abline(v=11,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=11-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=11-adj,y=30,labels = "C")

# mark complete vib
#abline(v=43,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=43-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=43-adj,y=30,labels = "D")

# mark start rotation
#abline(v=50,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=50-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=50-adj,y=30,labels = "E")

# mark complete rotation
#abline(v=88,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=88-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=88-adj,y=30,labels = "F")

title(xlab="time (s)")
title(ylab="Mbps, VIBRANT slice")

# Flush output to PDF
dev.off()

# Start pdf driver
pdf(file="t09_h5bandwidth_r1.pdf", height=4, width=8)

# Plot
#plot(t05_data[,4], t05_data[,8], type="n", xlim=c(min_x, max_x), ann=FALSE)
plot(t09_h5bandwidth, type="n", col=plot_colors[1], ann=FALSE, mgp=c(3, 0.5, 0), ylim=c(min_y, max_y), xlim=c(0, max_x))
lines(t09_h5bandwidth, type="b", pch=20)
axis(1,at=phvals1,labels=phlabels1,las=1,mgp=c(3, 1.5, 0))
axis(1,at=phvals2,labels=phlabels2,las=1,mgp=c(3, 1.5, 0))

# lty 3 == dotted
# mark start h1
#abline(v=2,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=2-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=2-adj,y=30,labels = "A")

# mark start h5
#abline(v=4,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=4-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=4-adj,y=30,labels = "B")

# mark start vib
#abline(v=11,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=11-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=11-adj,y=30,labels = "C")

# mark complete vib
#abline(v=43,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=43-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=43-adj,y=30,labels = "D")

# mark start rotation
#abline(v=50,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=50-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=50-adj,y=30,labels = "E")

# mark complete rotation
#abline(v=88,col=plot_colors[2],lty="dashed", lwd=2)
draw.circle(x=88-adj,y=30,radius=1.25,lty=1,lwd=1,col="white")
text(x=88-adj,y=30,labels = "F")

title(xlab="time (s)")
title(ylab="Mbps, non-VIBRANT slice")

# Flush output to PDF
dev.off()

# Start pdf driver
pdf(file="t09_h2latency_r1.pdf", height=4, width=8)

op <- par(mar=c(5,4,1,1))
plot(t09_h2latency, type="p", pch=".", col=plot_colors[1], ann=FALSE, mgp=c(3, 0.5, 0), xlab="")
axis(1,at=phvals1,labels=phlabels1,las=1,mgp=c(3, 1.5, 0))
axis(1,at=phvals2,labels=phlabels2,las=1,mgp=c(3, 1.5, 0))
par(op)

title(xlab="time (s)")
title(ylab="latency (ms)")

# Flush output to PDF
dev.off()

# Restore default margins
par(mar=c(5, 4, 4, 2) + 0.1)
