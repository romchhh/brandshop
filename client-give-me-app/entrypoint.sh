#!/bin/sh

# echo "Check that we have NEXT_PUBLIC_API_HOST vars"
# test -n "$NEXT_PUBLIC_API_HOST"

# find /app/.next \( -type d -name .git -prune \) -o -type f -print0 | xargs -0 sed -i "s#APP_NEXT_PUBLIC_API_HOST#$NEXT_PUBLIC_API_HOST#g"

# echo "Check that we have NEXT_PUBLIC_DEV vars"
# test -n "$NEXT_PUBLIC_DEV"

# find /app/.next \( -type d -name .git -prune \) -o -type f -print0 | xargs -0 sed -i "s#APP_NEXT_PUBLIC_DEV#$NEXT_PUBLIC_DEV#g"

echo "Starting Nextjs"
exec "$@"