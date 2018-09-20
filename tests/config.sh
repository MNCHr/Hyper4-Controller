#!/bin/bash

printf "#!/bin/bash\n\n" > ssh_vals.sh
printf "user=$1\n" >> ssh_vals.sh
printf "nodes=( $2 $3 $4 $5 $6 $7 $8 $9 ${10} ${11} ${12} )\n" >> ssh_vals.sh
