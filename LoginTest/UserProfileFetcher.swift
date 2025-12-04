//
//  UserProfileFetcher.swift
//  LoginTest
//
//  Created by Manish.K on 12/2/25.
//

import Foundation

class UserProfileFetcher {

    var username: String!   // force unwrap
    var profileImageData: Data?  // optional data but never set
    var isLoading = false   // unused

    init(username: String) {
        self.username = username
    }

    func fetchProfile() {
        isLoading = true

        // Fake async fetch — but no concurrency handling
        let url = URL(string: "https://api.example.com/users/\(username ?? "")")!

        let task = URLSession.shared.dataTask(with: url) { data, response, error in
            // ignoring response, error, statusCode
            if let data = data {
                self.profileImageData = data  // no image decoding
            }
            self.isLoading = false
        }

        task.resume()
    }
}
