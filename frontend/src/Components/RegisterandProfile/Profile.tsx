import React from 'react';
import './Profile.css';
import Register from './Register';


const Prof = () => {
    const information = (userData: { name: string; email: string; password: string }) => {
        const User: { name: string; email: string; password: string } = userData;
        return(
            <div className="menu-container">
                {User.name}
                {User.email}
                {User.password}
            </div>
        )
    };

    return (
        <Register onRegister={information}></Register>
    );
};

export default Prof;