#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script needs to be run as root" >&2
   exit 1
fi



custom_sizes=(
  "2,3"
  "2,4"
  "2,5"
  "2,6"
  "2,7"
  "2,8"
  "3,4"
  "3,5"
  "3,6"
  "3,7"
  "3,8"
  "4,5"
  "4,6"
  "4,7"
  "4,8"
  "5,6"
  "5,7"
  "5,8"
  "6,7"
  "6,8"
  "7,8"
)

check_files=(
    "alive/alive_result_32.txt"
    "alive/alive_result_64.txt"
    "alive/alive_result_128.txt"
    "not_alive/not_alive_result_32.txt"
    "not_alive/not_alive_result_64.txt"
    "not_alive/not_alive_result_128.txt"
)

output_file="results_summary.csv"



# helper function to delete the files created by the run.sh script
delete_check_files() {
    for file in "${check_files[@]}"; do
        rm -f "$file"
    done
}


# count occurrences of the exact provided string in some file
count_string() { 
    local string="$1" 
    local file="$2" 
    
    grep -oF "$string" "$file" | wc -l 
}


echo "Removing older files"
rm -f $output_file
delete_check_files

echo "Starting sweep across different window settings. The output will be saved into the configured CSV file"

# insert the CSV header into the output file
{ 
    printf "lower,upper" 
    for file in "${check_files[@]}"; do 
        # turn path into a safe CSV column prefix 
        column="${file//\//_}" 
        column="${column//./_}" 
        
        printf ",%s_target_alive,%s_target_not_alive" "$column" "$column" 
    done 
    
    printf "\n"
} > "$output_file"



for size in "${custom_sizes[@]}"; do
    IFS=',' read -r lower upper <<< "$size"

    # configure the window size
    sysctl -w "net.ipv4.tcp_syn_backlog_lower_bound_factor=$lower"
    sysctl -w "net.ipv4.tcp_syn_backlog_upper_bound_factor=$upper"

    echo "Running the tests with window size set between $lower and $upper"
    ./run.sh

    
    printf "%s,%s" "$lower" "$upper" >> "$output_file" # saving window settings inside the CSV file
    for file in "${check_files[@]}"; do                # counting the number of "alive" and "not alive" strings in each file
        alive_count=$(count_string "Target alive" "$file") 
        not_alive_count=$(count_string "Target not alive" "$file") 
        printf ",%s,%s" "$alive_count" "$not_alive_count" >> "$output_file" 
    done 
    printf "\n" >> "$output_file"

    delete_check_files
done

echo "Results written to $output_file"