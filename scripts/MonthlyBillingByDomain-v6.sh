#!/bin/bash

# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

# Variable for the current date
current_date=$(date '+%Y-%m-%d')

# Function to get accounts excluding specified patterns
get_accounts() {
  domain="$1"
  /opt/zimbra/common/bin/ldapsearch -o ldif-wrap=no -x -H $ldap_single_master_url -D $zimbra_ldap_userdn -w $zimbra_ldap_password -LLL '(&(objectClass=zimbraAccount)(ou:dn:=people)(zimbraMailDeliveryAddress='*@$domain'))' zimbraMailDeliveryAddress | egrep "^zimbraMailDeliveryAddress: " | awk '{print $2}' | sort | grep -v "ham\.\|spam.\|virus\.\|galsync"
}

# Function to get class of service id
get_cos_id() {
  local cos="$1"
  local cos_id=$(/opt/zimbra/bin/zmprov gc "$cos" zimbraId | awk '/zimbraId:/ {print $2}')
  echo "$cos_id"
}

# Function to get class of service id for an account
get_account_cos_id() {
  local account="$1"
  local domain_cos="$2"
  local cos_id=`/opt/zimbra/common/bin/ldapsearch -o ldif-wrap=no -x -H $ldap_single_master_url -D $zimbra_ldap_userdn -w $zimbra_ldap_password -LLL '(&(objectClass=zimbraAccount)(ou:dn:=people)(zimbraMailDeliveryAddress='$account'))' zimbraCOSId | egrep "^zimbraCOSId: " | awk '{print $2}'`
  if [[ -z $cos_id ]]; then
    # Account using domain default CoS so return that
    cos_id="$domain_cos"
  fi
  echo "$cos_id"
}

# Set the ldap variables for searching
source ~/bin/zmshutil ; zmsetvars
ldap_single_master_url=`echo $ldap_master_url | awk '{print $1}'`

# Moved the CoS array population out of the domain loop
# Get a list of all plain-English names of available Classes of Service
cos_list=($(/opt/zimbra/bin/zmprov gac | sort | awk '{print $1}'))

# Create a temporary associative array to store COS names and their IDs
declare -A cos_id_map

# Loop through COS names and populate the associative array
for cos_name in "${cos_list[@]}"; do
  cos_id=$(get_cos_id "$cos_name")
  cos_id_map["$cos_id"]=$cos_name
done

# Build list of local domains from ldap
filtered_domains=`/opt/zimbra/common/bin/ldapsearch -o ldif-wrap=no -x -H $ldap_single_master_url -D $zimbra_ldap_userdn -w $zimbra_ldap_password -LLL '(&(objectClass=zimbraDomain)(zimbraDomainType=local))' zimbraDomainName | egrep "^zimbraDomainName: " | awk '{print $2}' | sort`

# Get the default CoS ID
default_cos_id=`/opt/zimbra/bin/zmprov gc default zimbraId | egrep "^zimbraId: " | awk '{print $2}'`

echo "------------------------------------------------------------"
echo "| Zimbra Mailbox Usage Report for $current_date"
echo "------------------------------------------------------------"

# Loop through local domains and generate report
for domain in $filtered_domains; do
  echo "------------------------------------------------------------"
  echo "| CoS Usage for $domain:"
  echo "------------------------------------------------------------"

  # Get the domains default CoS ID
  domain_cos_id=`/opt/zimbra/common/bin/ldapsearch -o ldif-wrap=no -x -H $ldap_single_master_url -D $zimbra_ldap_userdn -w $zimbra_ldap_password -LLL '(&(objectClass=zimbraDomain)(zimbraDomainName='$domain'))' zimbraDomainDefaultCOSId | egrep "^zimbraDomainDefaultCOSId: " | awk '{print $2}'`
  if [[ -z $domain_cos_id ]]; then
    # There's no default CoS set at the domain level so use the system wide default
    domain_cos_id="$default_cos_id"
  fi

  # Get a list of accounts at this domain
  account_by_domain=($(get_accounts "$domain" | grep "@$domain" | sort -t '@' -k2,2r))

  # Initialize an associative array for counting
  declare -A cos_count

  # Loop through accounts in the domain and count the occurrences of each COS
  for account in "${account_by_domain[@]}"; do
    # Extract the domain from the account
    account_domain=$(echo "$account" | cut -d "@" -f 2)
    if [ "$account_domain" == "$domain" ]; then
      cos_id=$(get_account_cos_id "$account" "$domain_cos_id")
      cos_name="${cos_id_map[$cos_id]}"
      if [ -n "$cos_name" ]; then
        ((cos_count["$cos_name"]++))
      fi
    fi
  done

  # Print the report for the current domain
  for cos_name in "${!cos_count[@]}"; do
    count="${cos_count["$cos_name"]}"
    echo "- $cos_name: $count"
  done

  # Clear the associative arrays for the next domain
  unset cos_count

  echo "------------------------------------------------------------"
  echo
done
