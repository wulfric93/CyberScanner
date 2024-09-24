import dns.resolver
import time
import sys
import itertools
import ipaddress
import threading
import pandas as pd
from datetime import datetime
import os

# Expanded list of public DNS resolvers (IPv4 and IPv6)
dns_servers = [
    # Google DNS
    '8.8.8.8', '8.8.4.4', '2001:4860:4860::8888', '2001:4860:4860::8844',
    # Cloudflare DNS
    '1.1.1.1', '1.0.0.1', '2606:4700:4700::1111', '2606:4700:4700::1001',
    # OpenDNS (Cisco)
    '208.67.222.222', '208.67.220.220', '2620:119:35::35', '2620:119:53::53',
    # Quad9
    '9.9.9.9', '2620:fe::fe',
    # DNS.Watch
    '84.200.69.80', '84.200.70.40', '2001:1608:10:25::1c04:b12f', '2001:1608:10:25::9249:d69b',
    # CleanBrowsing
    '185.228.168.168', '185.228.169.168', '2a0d:2a00:1::2', '2a0d:2a00:2::2',
    '185.228.168.9', '185.228.169.9', '2a0d:2a00:1::1', '2a0d:2a00:2::1',
    # Comodo Secure DNS
    '8.26.56.26', '8.20.247.20',
    # OpenNIC
    '73.55.80.170', '198.50.184.208', '2001:67c:28a4::', '2001:67c:28a4:1::',
    # Yandex DNS
    '77.88.8.8', '77.88.8.1', '2a02:6b8::', '2a02:6b8::1',
    '77.88.8.88', '77.88.8.2', '2a02:6b8::8888', '2a02:6b8::8882',
    # Verisign
    '64.6.64.6', '64.6.65.6', '2620:74:1b::1', '2620:74:1c::2',
    # Hurricane Electric
    '74.82.42.42', '2001:470:20::2', '2001:470:30::2',
    # NTT
    '129.250.35.250', '129.250.35.251', '2001:2000::1', '2001:2000:2::2',
    # SafeDNS
    '195.46.39.39', '195.46.39.40',
    # Dyn
    '216.146.35.35', '216.146.36.36',
    # Alternate DNS
    '198.101.242.72', '23.253.163.53', '2606:4700:4700::1111', '2606:4700:4700::1001'
]

# Spinner animation for query progress
def spinner():
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if done:
            break
        sys.stdout.write('\rQuerying... ' + c)
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\rQuerying... Done!    \n')

# Clear the screen
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Get all IPs associated with a domain or subdomain
def get_all_ips_for_subdomain(subdomain, attempts=3):
    global done
    ips = set()  # Use a set to avoid duplicates

    for dns_server in dns_servers:
        clear_screen()  # Clear the screen before each DNS server query
        print(f"\nQuerying DNS server: {dns_server}")

        resolver = dns.resolver.Resolver()
        resolver.nameservers = [dns_server]
        resolver.timeout = 5  # Increased timeout
        resolver.lifetime = 10  # Increased lifetime of the query
        resolver.use_edns(0, dns.flags.DO, 4096)  # Use EDNS for larger responses

        # Start the loading spinner in a separate thread
        done = False
        spinner_thread = threading.Thread(target=spinner)
        spinner_thread.start()
        
        for attempt in range(attempts):
            print(f"Attempt {attempt + 1}/{attempts}")
            try:
                # Query for A (IPv4) records
                try:
                    print(f"Querying A (IPv4) records for {subdomain}...")
                    answer_a = resolver.resolve(subdomain, 'A')
                    ips.update([ip.to_text() for ip in answer_a])
                except dns.resolver.NoAnswer:
                    print(f"No A (IPv4) records found for {subdomain}")
                
                # Query for AAAA (IPv6) records
                try:
                    print(f"Querying AAAA (IPv6) records for {subdomain}...")
                    answer_aaaa = resolver.resolve(subdomain, 'AAAA')
                    ips.update([ip.to_text() for ip in answer_aaaa])
                except dns.resolver.NoAnswer:
                    print(f"No AAAA (IPv6) records found for {subdomain}")
                
                # Query for CNAME records and resolve again
                try:
                    print(f"Querying CNAME records for {subdomain}...")
                    answer_cname = resolver.resolve(subdomain, 'CNAME')
                    cname = [cname_record.to_text() for cname_record in answer_cname]
                    print(f"CNAME record found: {cname}")
                    # Resolve the CNAME as well
                    for alias in cname:
                        print(f"Resolving CNAME {alias}...")
                        ips.update(get_all_ips_for_subdomain(alias))  # Recursively resolve CNAMEs
                except dns.resolver.NoAnswer:
                    pass  # No CNAME record found
            
            except dns.resolver.NXDOMAIN:
                print(f"Domain does not exist: {subdomain}")
            except dns.resolver.NoNameservers:
                print(f"No nameservers responded for {subdomain}")
            except dns.exception.Timeout:
                print(f"Query timeout for {subdomain}")
            except Exception as e:
                print(f"Error occurred: {e}")
        
        done = True
        spinner_thread.join()  # Stop the spinner

        # Short delay between DNS queries to avoid throttling
        time.sleep(1)
    
    return ips

# Sort IP addresses
def sort_ips(ip_list):
    def sort_key(ip):
        try:
            # Sort IPv4 addresses numerically
            return (0, ipaddress.IPv4Address(ip))
        except ipaddress.AddressValueError:
            # Sort IPv6 addresses lexicographically
            return (1, ipaddress.IPv6Address(ip))
    
    return sorted(ip_list, key=sort_key)

# Write results to an Excel file
def write_to_excel(domain, ips):
    filename = f"{domain}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
    df = pd.DataFrame({
        'IP Address': ips,
        'Domain': domain,
        'Date of Scan': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    df.to_excel(filename, index=False)
    print(f"Results have been saved to {filename}")

# Ask the user for a domain or subdomain
if __name__ == "__main__":
    done = False
    
    subdomain = input("Enter the domain or subdomain: ")

    # Start querying for all IPs
    ips = get_all_ips_for_subdomain(subdomain, attempts=5)  # Increase attempts to 5

    if ips:
        sorted_ips = sort_ips(ips)
        print(f"\nIP addresses for {subdomain}:")
        for ip in sorted_ips:
            print(ip)
        
        # Write results to an Excel file
        write_to_excel(subdomain, sorted_ips)
    else:
        print(f"No IPs found for {subdomain}")
