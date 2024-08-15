#!/bin/bash

cat <<EOL > access.log
192.168.1.1 - - [28/Jul/2024:12:34:56 +0000] "GET /index.html HTTP/1.1" 200 1234
192.168.1.2 - - [28/Jul/2024:12:35:56 +0000] "POST /login HTTP/1.1" 200 567
192.168.1.3 - - [28/Jul/2024:12:36:56 +0000] "GET /home HTTP/1.1" 404 890
192.168.1.1 - - [28/Jul/2024:12:37:56 +0000] "GET /index.html HTTP/1.1" 200 1234
192.168.1.4 - - [28/Jul/2024:12:38:56 +0000] "GET /about HTTP/1.1" 200 432
192.168.1.2 - - [28/Jul/2024:12:39:56 +0000] "GET /index.html HTTP/1.1" 200 1234
EOL

total_requests=$(wc -l < access.log)

unique_ips=$(awk '{print $1}' access.log | sort -u | wc -l)

request_methods=$(awk '{print $6}' access.log | sed 's/"//g' | sort | uniq -c | awk '
    {
        print "\t" $2, $1
    }')
# Найти самый популярный URL
popular_url=$(awk '{print $7}' access.log | sed 's/"//g' | sort | uniq -c | sort -nr | head -1)
popular_url_count=$(echo "$popular_url" | awk '{print $1}')
popular_url_url=$(echo "$popular_url" | awk '{print $2}')

# Создание отчета
cat << EOF > report.txt
Общее количество запросов: $total_requests
Количество уникальных IP-адресов: $unique_ips
Количество запросов по методам: 
$request_methods
Самый популярный URL: $popular_url_count $popular_url_url
EOF

echo "Отчет сгенерирован в файле report.txt"
