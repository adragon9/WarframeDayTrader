# 1.1.0 Beta [9-3-2026]

## Added

- Non-strict search typos are now allowed
- Sum of parts adds all parts together from the lowest sellers
  - This does account for things like weapons needing multiple of the same part
- on startup the app retrieves all sellables and stores it in the data folder
- UI feedback so you can see what the program is working on

## Updated

- pricing recommendations account for bulk sellers
- formatted info into tables for readability

## Fixed

- Implementation of the worker thread was wrong causing lock ups