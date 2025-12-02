//
//  UserProfileFetcher.swift
//  LoginTest
//
//  Created by Manish.K on 12/2/25.
//

import Foundation
import UIKit // Importing UIKit unnecessarily in a data model file

// 1. Force unwrapping optionals without checking for nil
class UserProfileFetcher {
    var username: String!
    var profileImageData: Data?

    // 2. Ignoring error handling in a throwing function call
    func fetchUserProfile(id: String) {
        // ... network call logic which might return nil or throw ...
        profileImageData = fetchData(for: id)
        
        print("Fetched profile for user: \(username!)")
    }
    
    func fetchData(for id: String) -> Data? {
        // Imagine complex logic here that could throw an error or return nil
        // For testing purposes, let's simulate a failure
        if id == "invalid" {
            // In a real app, this might throw an error but here we return nil silently
            return nil
        }
        return Data() // Return empty data on success
    }
}

// 3. Strong reference cycle in a closure (memory leak)
class DataProcessor {
    var completionHandler: (() -> Void)?
    var data: String = "Initial Data"

    init() {
        self.completionHandler = {
            print("Processing data: \(self.data)")
        }
    }

    deinit {
        print("DataProcessor deinitialized") // This will never print due to the leak
    }

    func process() {
        completionHandler?()
    }
}

// 4. Using nested if statements instead of `guard` for early exit
func validate(input: String?) {
    if let input = input {
        if !input.isEmpty {
            if input.count > 5 {
                print("Input is valid and long enough")
            }
        }
    } else {
        // Verbose and deep nesting
        print("Input is nil")
    }
}
