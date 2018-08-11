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
t09_l2_addresses <- read.table("data/t09_analysis_l2_addresses_r1",header=TRUE,sep=",")
t09_l3_addresses <- read.table("data/t09_analysis_l3_addresses_r1",header=TRUE,sep=",")
t09_h2latency <-read.table("data/t09_analysis_latency_r1",header=TRUE,sep=",")
t09_h2latency_p95 <- read.table("data/t09_analysis_latency_p95_r1",header=TRUE,sep=",")
t09_h1bandwidth <- read.table("data/t09_analysis_h1bandwidth_r1",header=TRUE,sep=",")
t09_h5bandwidth <- read.table("data/t09_analysis_h5bandwidth_r1",header=TRUE,sep=",")

phvals1=c(2, 11, 43, 50, 88)
phlabels1=c("A", "C", "D", "E", "F")
phvals2=c(4)
phlabels2=c("B")

plot_colors <- c("black","red")

# ------ L2 Addresses ------

# Start pdf driver
pdf(file="plots/t09_l2_addresses_r1.pdf", height=4, width=8)

# Trim excess margin space
par(mar=c(4.2, 3.9, 0.2, 0.5))

# Get range
max_y <- max(t09_l2_addresses)

# Plot
plot(t09_l2_addresses, type="p", pch=".", col=plot_colors[1], ann=FALSE, yaxt="n", mgp=c(3, 0.5, 0))

maclabels <- c("00:*","20:*","40:*","60:*","80:*","A0:*","C0:*","E0:*")
macvals <- c(0, max_y/8, 2*max_y/8, 3*max_y/8, 4*max_y/8, 5*max_y/8, 6*max_y/8, 7*max_y/8)
axis(2,at=macvals,labels=maclabels,las=2)
axis(1,at=phvals1,labels=phlabels1,las=1,mgp=c(3, 1.5, 0))
axis(1,at=phvals2,labels=phlabels2,las=1,mgp=c(3, 1.5, 0))

title(xlab="time (s)")
title(ylab="MAC address")

# Flush output to PDF
dev.off()

# ------ L3 Addresses ------

# Start pdf driver
pdf(file="plots/t09_l3_addresses_r1.pdf", height=4, width=8)

# Trim excess margin space
par(mar=c(4.2, 3.9, 0.2, 0.5))

# Get range
max_y <- max(t09_l3_addresses)

# Plot
plot(t09_l3_addresses, type="p", pch=".", col=plot_colors[1], ann=FALSE, yaxt="n", mgp=c(3, 0.5, 0))

iplabels <- c("0.*","32.*","64.*","96.*","128.*","160.*","192.*","224.*")
ipvals <- c(0, max_y/8, 2*max_y/8, 3*max_y/8, 4*max_y/8, 5*max_y/8, 6*max_y/8, 7*max_y/8)
axis(2,at=ipvals,labels=iplabels,las=2, cex.axis=0.5)
axis(1,at=phvals1,labels=phlabels1,las=1,mgp=c(3, 1.5, 0))
axis(1,at=phvals2,labels=phlabels2,las=1,mgp=c(3, 1.5, 0))

title(xlab="time (s)")
title(ylab="IP address")

# Flush output to PDF
dev.off()

# ------ X axis limits for bandwidth plots ------

max_y_h1 <- max(t09_h1bandwidth[[2]])
max_y_h5 <- max(t09_h5bandwidth[[2]])
max_y <- max(max_y_h1,max_y_h5)

min_y_h1 <- min(t09_h1bandwidth[[2]])
min_y_h5 <- min(t09_h5bandwidth[[2]])
min_y <- min(min_y_h1,min_y_h5)

max_x <- max(t09_h1bandwidth[[1]])

# ------ H1 Bandwidth ------

# Start pdf driver
pdf(file="plots/t09_bandwidth_r1.pdf", height=4, width=8)

# Trim excess margin space
par(mar=c(4.2, 3.9, 0.2, 0.5))

# Plot
#plot(t05_data[,4], t05_data[,8], type="n", xlim=c(min_x, max_x), ann=FALSE)
plot(t09_h1bandwidth, type="n", col=plot_colors[1], ann=FALSE, mgp=c(3, 0.5, 0), ylim=c(min_y, max_y), xlim=c(0, max_x))
lines(t09_h1bandwidth, type="b", pch=20)
points(t09_h5bandwidth, type="n", col=plot_colors[2], ann=FALSE, mgp=c(3, 0.5, 0), ylim=c(min_y, max_y), xlim=c(0, max_x))
lines(t09_h5bandwidth, type="b", pch=18, col=plot_colors[2])
axis(1,at=phvals1,labels=phlabels1,las=1,mgp=c(3, 1.5, 0))
axis(1,at=phvals2,labels=phlabels2,las=1,mgp=c(3, 1.5, 0))

title(xlab="time (s)")
title(ylab="Mbps")

# Create legend
legend("topright", c("slice 1: h1 <-> h3","slice 2: h5 <-> h6"), col=plot_colors, pch=c(20,18), cex=0.8, box.lwd = 0, box.col = "white", bg = "white", inset=c(0.01, 0.01))

# Flush output to PDF
dev.off()

# ------ H5 Bandwidth ------

# Start pdf driver
#pdf(file="t09_h5bandwidth_r1.pdf", height=4, width=8)

# Trim excess margin space
#par(mar=c(4.2, 3.9, 0.2, 0.5))

# Plot
#plot(t09_h5bandwidth, type="n", col=plot_colors[1], ann=FALSE, mgp=c(3, 0.5, 0), ylim=c(min_y, max_y), xlim=c(0, max_x))
#lines(t09_h5bandwidth, type="b", pch=20)
#axis(1,at=phvals1,labels=phlabels1,las=1,mgp=c(3, 1.5, 0))
#axis(1,at=phvals2,labels=phlabels2,las=1,mgp=c(3, 1.5, 0))

#title(xlab="time (s)")
#title(ylab="Mbps, non-VIBRANT slice")

# Flush output to PDF
#dev.off()

# ------ H2 Latency ------

# Start pdf driver
pdf(file="plots/t09_h2latency_r1.pdf", height=4, width=8)

op <- par(mar=c(5,4,1,1))
plot(t09_h2latency, type="p", pch=".", col=plot_colors[1], ann=FALSE, mgp=c(3, 0.5, 0), xlab="")
axis(1,at=phvals1,labels=phlabels1,las=1,mgp=c(3, 1.5, 0))
axis(1,at=phvals2,labels=phlabels2,las=1,mgp=c(3, 1.5, 0))
par(op)

title(xlab="time (s)")
title(ylab="latency (ms)")

# Flush output to PDF
dev.off()
